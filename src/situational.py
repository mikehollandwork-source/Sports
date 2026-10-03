"""
Who hits with runners on — one team's lineup, by situational split.

READ-ONLY. Changes no pick, writes no ledger entry.

THE SPLIT CODES ARE DISCOVERED, NOT GUESSED
MLB's statSplits endpoint takes `sitCodes`, and the valid set is served by
/api/v1/situationCodes. This fetches that list and reports which codes it used, so
a renamed or missing code shows up as "not returned" instead of being silently
dropped or, worse, guessed at. `--codes` prints the whole catalogue.

READ THE SAMPLE
A season's runners-on sample is a few hundred plate appearances; RISP is smaller
still, often under 150. Clutch hitting has famously little year-to-year
persistence, so a high RISP line is mostly a record of what happened, not a skill
that carries into tonight. The plain overall line is printed beside each split for
exactly that reason - when the two are close, the split is telling you nothing the
overall number did not.

Writes output/situational.md.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from . import mlb_api
from .mlb_api import lineup, schedule_for

log = logging.getLogger("situational")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# what we want, in priority order; matched against the live catalogue by code
WANTED = ("risp", "men_on", "runners_on", "bases_loaded", "nobody_on", "empty")


def situation_codes() -> dict:
    """{code: description} from MLB's own catalogue of valid sitCodes."""
    out: dict = {}
    try:
        data = mlb_api._get("situationCodes")
    except Exception as exc:
        log.warning("situationCodes fetch failed: %s", exc)
        return out
    rows = data if isinstance(data, list) else (data.get("situationCodes") or [])
    for r in rows:
        if isinstance(r, dict) and r.get("code"):
            out[str(r["code"]).lower()] = r.get("description") or r.get("name") or ""
    return out


def player_splits(player_id: int, season: int, codes: list[str]) -> dict:
    """{code: stat} for one player. One request with every code, as the endpoint
    accepts a comma list."""
    out: dict = {}
    if not codes:
        return out
    try:
        data = mlb_api._get(f"people/{player_id}/stats", stats="statSplits",
                            group="hitting", season=season,
                            sitCodes=",".join(codes))
    except Exception as exc:
        log.warning("splits failed for %s: %s", player_id, exc)
        return out
    for s in data.get("stats", []):
        for sp in s.get("splits", []):
            code = str((sp.get("split") or {}).get("code", "")).lower()
            if code:
                out[code] = sp.get("stat") or {}
    return out


def season_line(player_id: int, season: int) -> dict:
    try:
        data = mlb_api._get(f"people/{player_id}/stats", stats="season",
                            group="hitting", season=season)
    except Exception:
        return {}
    for s in data.get("stats", []):
        for sp in s.get("splits", []):
            return sp.get("stat") or {}
    return {}


def _n(st: dict, *keys):
    for k in keys:
        v = st.get(k)
        if v not in (None, "", "-", ".---"):
            return v
    return "—"


def _line(st: dict) -> str:
    if not st:
        return "—"
    return (f"{_n(st,'plateAppearances')} PA · {_n(st,'avg')}/{_n(st,'obp')}/"
            f"{_n(st,'slg')} · OPS {_n(st,'ops')}")


def _ops(st: dict) -> float | None:
    try:
        return float(st.get("ops"))
    except (TypeError, ValueError):
        return None


def build(team_name: str, date: str) -> str:
    md = [f"# {team_name} — hitting with runners on, {date}", "",
          "_Read-only: changes no pick._", "",
          "_**Clutch splits barely persist year to year.** A RISP sample is often "
          "under 150 PA, so a big number here is a record of what happened rather "
          "than a skill that carries into tonight. The overall line sits beside "
          "each split: when they are close, the split adds nothing._", ""]
    catalogue = situation_codes()
    if not catalogue:
        md.append("_Could not fetch MLB's situationCodes catalogue; "
                  "falling back to the requested codes._")
    use = [c for c in WANTED if not catalogue or c in catalogue]
    md += ["", f"- codes used: {', '.join(use) if use else 'none'}",
           "- not in MLB's catalogue: "
           + (", ".join(c for c in WANTED if catalogue and c not in catalogue)
              or "none"), ""]

    games = schedule_for(date)
    gm = next((g for g in games if team_name in (g.away.name, g.home.name)), None)
    if gm is None:
        return "\n".join(md + [f"No {team_name} game on {date}.", ""])
    is_home = gm.home.name == team_name
    team = gm.home if is_home else gm.away
    try:
        bats = lineup(gm.game_pk, team.team_id, date, is_home)
    except Exception as exc:
        return "\n".join(md + [f"Lineup unavailable ({exc}).", ""])
    if not bats:
        return "\n".join(md + ["No lineup posted yet.", ""])

    season = int(date[:4])
    rows = []
    for p in bats:
        sp = player_splits(p.player_id, season, use)
        overall = season_line(p.player_id, season)
        risp = sp.get("risp") or {}
        rows.append({"name": p.name, "overall": overall, "risp": risp,
                     "splits": sp,
                     "lift": (_ops(risp) - _ops(overall))
                             if _ops(risp) is not None and _ops(overall) is not None
                             else None})
    ranked = sorted(rows, key=lambda r: -(_ops(r["risp"]) or -9))

    md += ["## With runners in scoring position", "",
           "| hitter | RISP | overall | RISP − overall |", "|---|---|---|---|"]
    for r in ranked:
        lift = f"**{r['lift']:+.3f}**" if r["lift"] is not None else "—"
        md.append(f"| {r['name']} | {_line(r['risp'])} | {_line(r['overall'])} "
                  f"| {lift} |")
    md.append("")

    other = [c for c in use if c != "risp"]
    if other:
        md += ["## The other situational splits", "",
               "| hitter | " + " | ".join(
                   f"{c} ({catalogue.get(c, '')})".strip() for c in other) + " |",
               "|---|" + "---|" * len(other)]
        for r in sorted(rows, key=lambda x: x["name"]):
            md.append(f"| {r['name']} | "
                      + " | ".join(_line(r["splits"].get(c) or {}) for c in other)
                      + " |")
        md.append("")
    return "\n".join(md + [""])


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default=os.environ.get("SIT_TEAM") or "")
    ap.add_argument("--date", default=os.environ.get("PICKS_DATE"))
    ap.add_argument("--codes", action="store_true",
                    help="print MLB's situationCodes catalogue and exit")
    a = ap.parse_args()
    if a.codes or os.environ.get("SIT_CODES") == "1":
        cat = situation_codes()
        lines = [f"# MLB situationCodes ({len(cat)})", ""] + \
                [f"- `{c}` — {d}" for c, d in sorted(cat.items())]
        md = "\n".join(lines)
    else:
        if not a.team:
            print("pass --team")
            return
        date = a.date
        if not date:
            from .main import today_eastern
            date = today_eastern()
        md = build(a.team, date)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "situational.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
