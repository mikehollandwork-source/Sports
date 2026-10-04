"""
Probe: do MLB's pitch-type splits carry home runs, for hitters AND pitchers?

WHY PROBE FIRST
The plan is to match a hitter's power BY PITCH TYPE against a starter's pitch
MIX - if a hitter only homers on fastballs and the starter throws 60% fastballs,
that is a real matchup. The whole idea rests on two things being true, and
neither has been checked:

  1. a HITTER's statSplits by pitch type carry homeRuns and plateAppearances
  2. a PITCHER's do too, so his PA-by-type gives his usage mix and his HR-by-type
     says which pitch gets hit out

If either is missing the idea is dead and should be abandoned rather than
approximated. Also reports the SAMPLE per type, because a hitter with 17 home
runs spread over five pitch types has 3-4 per type and that is the real
constraint on how much weight any of this can carry.

Writes output/pitchtype_probe.md.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from . import mlb_api

log = logging.getLogger("pitchtype_probe")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# from /api/v1/situationCodes, the pitch types that actually matter
CODES = ["pfa", "pff", "pft", "psi", "pfc", "psl", "pcu", "pkc", "pch", "pfs"]
LABEL = {"pfa": "Fastball", "pff": "Four-seam", "pft": "Two-seam",
         "psi": "Sinker", "pfc": "Cutter", "psl": "Slider",
         "pcu": "Curveball", "pkc": "Knuckle curve", "pch": "Changeup",
         "pfs": "Splitter"}


def splits(player_id: int, group: str, season: int) -> dict:
    """{code: stat} for a player's pitch-type splits."""
    out: dict = {}
    try:
        data = mlb_api._get(f"people/{player_id}/stats", stats="statSplits",
                            group=group, season=season,
                            sitCodes=",".join(CODES))
    except Exception as exc:
        log.warning("%s splits failed for %s: %s", group, player_id, exc)
        return out
    for s in data.get("stats", []):
        for sp in s.get("splits", []):
            code = str((sp.get("split") or {}).get("code", "")).lower()
            if code:
                out[code] = sp.get("stat") or {}
    return out


def _n(st: dict, key: str):
    v = st.get(key)
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _table(rows: dict, group: str) -> list[str]:
    md = ["| pitch | PA | HR | HR/PA | fields present |", "|---|---|---|---|---|"]
    tot_pa = tot_hr = 0
    for c in CODES:
        st = rows.get(c)
        if not st:
            md.append(f"| {LABEL[c]} (`{c}`) | — | — | — | _not returned_ |")
            continue
        pa, hr = _n(st, "plateAppearances"), _n(st, "homeRuns")
        has = ", ".join(k for k in ("plateAppearances", "homeRuns", "atBats",
                                    "slg", "totalBases") if k in st) or "none"
        rate = f"{hr/pa:.2%}" if pa and hr is not None else "—"
        if pa:
            tot_pa += pa
        if hr:
            tot_hr += hr
        md.append(f"| {LABEL[c]} (`{c}`) | {pa} | {hr} | {rate} | {has} |")
    md += ["", f"- totals across types: **{tot_pa} PA, {tot_hr} HR**",
           "- _if the totals look like a full season the types partition it; "
           "if they far exceed it, the codes overlap (e.g. `pfa` containing "
           "`pff`+`pft`) and only ONE family may be summed_", ""]
    return md


def alt_endpoints(player_id: int, group: str, season: int) -> list[str]:
    """Try the OTHER places MLB might serve pitch-mix data.

    statSplits with the pitch-type sitCodes came back empty for both groups,
    while vr/vl on the SAME endpoint works (the platoon term uses it) - so
    statSplits is fine and the pitch-type codes are simply not populated. These
    are the documented alternatives, checked before the idea is abandoned.
    """
    out = []
    for stats in ("pitchArsenal", "pitchLog", "playLog", "hotColdZones",
                  "sabermetrics"):
        try:
            data = mlb_api._get(f"people/{player_id}/stats", stats=stats,
                                group=group, season=season)
        except Exception as exc:
            out.append(f"- `{stats}` ({group}): request failed — {exc}")
            continue
        blocks = data.get("stats") or []
        if not blocks:
            out.append(f"- `{stats}` ({group}): **empty**")
            continue
        n = sum(len(b.get("splits") or []) for b in blocks)
        keys = set()
        for b in blocks:
            for sp in (b.get("splits") or [])[:3]:
                keys |= set((sp.get("stat") or {}).keys())
        out.append(f"- `{stats}` ({group}): **{n} split(s)**, fields: "
                   + (", ".join(sorted(keys)[:14]) or "none"))
    return out


def shape(player_id: int, group: str, season: int) -> list[str]:
    """Dump the structure of a playLog/pitchArsenal record.

    pitchArsenal gives the MIX (type, usage%) but no outcomes; pitchLog/playLog
    give per-pitch records whose `play` may carry both the pitch type and the
    result. If it does, HR-by-pitch-type is computable for hitter AND pitcher
    from real pitch-level data - which is what the idea actually needs.
    """
    out = []
    try:
        ars = mlb_api._get(f"people/{player_id}/stats", stats="pitchArsenal",
                           group=group, season=season)
    except Exception as exc:
        out.append(f"- arsenal request failed: {exc}")
        ars = {}
    rows = []
    for b in ars.get("stats") or []:
        for sp in b.get("splits") or []:
            st = sp.get("stat") or {}
            t = st.get("type") or {}
            rows.append((st.get("percentage"), t.get("description") or t.get("code"),
                         st.get("count"), st.get("averageSpeed")))
    rows.sort(key=lambda r: -(r[0] or 0))
    out.append(f"**arsenal ({group})** — {len(rows)} type(s)")
    for pct, desc, cnt, spd in rows:
        out.append(f"  - {desc}: {pct}  (n={cnt}, {spd} mph)")

    try:
        pl = mlb_api._get(f"people/{player_id}/stats", stats="playLog",
                          group=group, season=season)
    except Exception as exc:
        out.append(f"- playLog request failed: {exc}")
        return out
    splits = [sp for b in (pl.get("stats") or []) for sp in (b.get("splits") or [])]
    out.append(f"**playLog ({group})** — {len(splits)} record(s)")
    if splits:
        out.append("one record, keys only:")
        out.append("```")
        out.append(json.dumps(_prune(splits[0]), indent=1)[:2600])
        out.append("```")
    # Does a HOME RUN record carry the pitch type?
    hrs = []
    for sp in splits:
        play = sp.get("play") or {}
        det = play.get("details") or {}
        ev = (det.get("event") or det.get("description") or "")
        if "home run" in ev.lower() or det.get("eventType") == "home_run":
            hrs.append(sp)
    out.append(f"**home-run records found: {len(hrs)}**")
    if hrs:
        play = hrs[0].get("play") or {}
        det = play.get("details") or {}
        ptype = (det.get("type") or {})
        out.append(f"  - first HR: event={det.get('event')!r} "
                   f"pitch={ptype.get('description') or ptype.get('code')!r} "
                   f"speed={(play.get('pitchData') or {}).get('startSpeed')!r}")
        tally: dict[str, int] = {}
        for h in hrs:
            d = ((h.get("play") or {}).get("details") or {})
            t = (d.get("type") or {}).get("description") or "?"
            tally[t] = tally.get(t, 0) + 1
        out.append("  - HR by pitch type: "
                   + ", ".join(f"{k} {v}" for k, v in
                               sorted(tally.items(), key=lambda kv: -kv[1])))
    return out


def _prune(obj, depth: int = 0):
    """Structure, not volume: keep keys and scalar samples, trim long lists."""
    if isinstance(obj, dict):
        return {k: _prune(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_prune(v, depth + 1) for v in obj[:2]]
    return obj


def resolve_starter(date: str) -> tuple[int, str]:
    """(id, name) of a probable starter on this date, so the probe needs no
    hand-copied player id."""
    try:
        for g in mlb_api.schedule_for(date):
            for t in (g.home, g.away):
                pp = getattr(t, "probable_pitcher", None)
                if pp and getattr(pp, "player_id", None):
                    return pp.player_id, pp.name
    except Exception as exc:
        log.warning("could not resolve a starter for %s: %s", date, exc)
    return 0, "no starter found"


def build(batter: int, pitcher: int, season: int,
          bname: str, pname: str) -> str:
    md = [f"# Pitch-type split probe — {season}", "",
          "_Does the idea have data under it? Checked before anything is built "
          "on it._", ""]
    for pid, group, who in ((batter, "hitting", bname),
                            (pitcher, "pitching", pname)):
        if not pid:
            continue
        md += [f"## {who} ({group}, id {pid})", ""]
        rows = splits(pid, group, season)
        if not rows:
            md += ["**Nothing returned.** The endpoint does not serve pitch-type "
                   "splits for this group, so this half of the idea is dead.", ""]
            continue
        md += _table(rows, group)
    md += ["## Alternative endpoints", "",
           "_statSplits serves vr/vl fine, so it is the pitch-type CODES that "
           "are unpopulated. These are the documented alternatives._", ""]
    if batter:
        md += alt_endpoints(batter, "hitting", season)
    if pitcher:
        md += alt_endpoints(pitcher, "pitching", season)
    md += ["", "## Pitch-level records", "",
           "_The real test: does a per-pitch record carry the pitch type AND "
           "the outcome? If yes, HR-by-pitch-type is computable directly._", ""]
    if batter:
        md += [f"### {bname} (hitting)", ""] + shape(batter, "hitting", season)
    if pitcher:
        md += ["", f"### {pname} (pitching)", ""] + shape(pitcher, "pitching", season)
    md += ["", "## What to conclude", "",
           "- both tables populated with PA and HR -> the matchup term is "
           "buildable, with heavy shrinkage for the per-type sample",
           "- a pitcher's PA per type doubles as his USAGE mix, which is the "
           "other half of the calculation",
           "- totals far above a season mean the codes OVERLAP and must not be "
           "summed naively", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--batter", type=int,
                    default=int(os.environ.get("PROBE_BATTER") or 0))
    ap.add_argument("--pitcher", type=int,
                    default=int(os.environ.get("PROBE_PITCHER") or 0))
    ap.add_argument("--season", type=int,
                    default=int(os.environ.get("PROBE_SEASON") or 2026))
    ap.add_argument("--bname", default=os.environ.get("PROBE_BNAME") or "batter")
    ap.add_argument("--pname", default=os.environ.get("PROBE_PNAME") or "pitcher")
    ap.add_argument("--date", default=os.environ.get("PICKS_DATE"))
    a = ap.parse_args()
    pitcher, pname = a.pitcher, a.pname
    if not pitcher:
        date = a.date
        if not date:
            from .main import today_eastern
            date = today_eastern()
        pitcher, pname = resolve_starter(date)
    md = build(a.batter, pitcher, a.season, a.bname, pname)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "pitchtype_probe.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
