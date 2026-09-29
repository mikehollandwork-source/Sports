"""
A team's record at a given price. `python -m src.team_at_odds "Atlanta Braves" -190`

Answers "how many times have they won at these odds recently" - a question the
board can already answer and never has, because every board file stores both
moneylines for every game whether or not it became a pick.

WHAT THE BAND IS FOR
Exact-price cells are tiny and meaningless: -190 alone might be four games. So
matches fall inside a band (default +/-20 cents, so -190 collects -170 to
-210), and the band is stated in the output rather than hidden, because a wide
band answers a slightly different question from the one asked.

WHAT THE BREAK-EVEN LINE IS FOR
A favourite's raw win rate says nothing on its own - -190 needs 65.5% just to
stay level. The report prints the record, the implied break-even, and the gap,
because "they won 6 of 9" is a loss at this price and reads like a win.

Both venues' prices are the board's, i.e. the price actually offered pre-game.
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
from pathlib import Path

from . import grade, mlb_api

log = logging.getLogger("team_at_odds")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _rows(team: str) -> list[dict]:
    """Every graded board game this team appeared in, with their own price."""
    out = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for g in json.loads(Path(f).read_text()).get("games", []):
            m = g.get("matchup") or ""
            res = results.get(g.get("game_pk"))
            if " @ " not in m or team not in m:
                continue
            if not res or not res.get("final") or not res.get("winner"):
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            away, home = m.split(" @ ")
            if team not in (away, home) or adv not in (away, home):
                continue
            odds = a_ml if team == adv else o_ml
            if not isinstance(odds, int):
                continue
            out.append({"date": date, "matchup": m, "odds": odds,
                        "won": res["winner"] == team,
                        "opp": home if team == away else away,
                        "score": f"{res.get('away_score')}-{res.get('home_score')}",
                        "home": team == home})
    return out


def _tally(rs: list[dict], odds: int) -> list[str]:
    if not rs:
        return ["_no games in this band._", ""]
    w = sum(1 for r in rs if r["won"])
    n = len(rs)
    u = sum(grade.american_profit(r["odds"]) if r["won"] else -1 for r in rs)
    be = (abs(odds) / (abs(odds) + 100)) if odds < 0 else (100 / (odds + 100))
    return [f"- record: **{w}-{n-w}** ({w/n:.0%})",
            f"- break-even at {odds:+d} is **{be:.0%}** — "
            + ("**clearing it**" if w / n > be else "**short of it**"),
            f"- flat-stake: **{u:+.2f}u** over {n} bets (**{u/n:+.1%}**)", ""]


def build(team: str, odds: int, band: int, recent: int) -> str:
    rows = _rows(team)
    lo, hi = odds - band, odds + band
    inband = [r for r in rows if lo <= r["odds"] <= hi]
    md = [f"# {team} at {odds:+d}", "",
          f"_Band {lo:+d} to {hi:+d} — an exact price is too few games to read. "
          f"Break-even is printed alongside the record because at {odds:+d} a "
          "winning record can still be a losing bet._", "",
          f"- graded games this season: **{len(rows)}**",
          f"- of those, priced in band: **{len(inband)}**", ""]
    md += ["## All season, in band", ""] + _tally(inband, odds)

    if recent and inband:
        days = sorted({r["date"] for r in rows})[-recent:]
        rec = [r for r in inband if r["date"] in set(days)]
        md += [f"## Last {recent} board days ({days[0]} onward)", ""] + _tally(rec, odds)

    fav = [r for r in inband if r["odds"] < 0]
    md += ["## Split by home and away, in band", "",
           "| | record | flat-stake |", "|---|---|---|"]
    for lab, sub in (("at home", [r for r in inband if r["home"]]),
                     ("on the road", [r for r in inband if not r["home"]])):
        if sub:
            w = sum(1 for r in sub if r["won"])
            u = sum(grade.american_profit(r["odds"]) if r["won"] else -1 for r in sub)
            md.append(f"| {lab} | {w}-{len(sub)-w} | {u:+.2f}u ({u/len(sub):+.1%}) |")
    md.append("")
    if fav:
        md += [f"_{len(fav)} of the {len(inband)} in-band games had them "
               "favoured._", ""]

    if inband:
        md += ["## The games", "", "| date | price | opponent | home | result |",
               "|---|---|---|---|---|"]
        for r in sorted(inband, key=lambda r: r["date"], reverse=True):
            md.append(f"| {r['date']} | {r['odds']:+d} | {r['opp']} | "
                      f"{'H' if r['home'] else 'A'} | "
                      f"{'**W**' if r['won'] else 'L'} |")
        md.append("")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("team")
    ap.add_argument("odds", type=int)
    ap.add_argument("--band", type=int, default=20)
    ap.add_argument("--recent", type=int, default=30,
                    help="also report the last N board days (0 to skip)")
    a = ap.parse_args()
    md = build(a.team, a.odds, a.band, a.recent)
    OUTPUT_DIR.mkdir(exist_ok=True)
    slug = a.team.split()[-1].lower()
    (OUTPUT_DIR / f"team_at_odds_{slug}.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
