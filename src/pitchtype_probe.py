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
