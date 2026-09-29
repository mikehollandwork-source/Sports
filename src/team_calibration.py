"""
Has the market been right about this team's price?
`python -m src.team_calibration "Philadelphia Phillies"`

WHY THIS AND NOT "RECORD AT THESE ODDS"
`team_at_odds` answers what was asked but cannot answer much: a price band
holds a handful of a team's games, and Philadelphia had been priced at +168
exactly zero times before today. Calibration uses every graded game the team
played, which is 80-odd rather than 11, and asks the better question - when the
market said 43%, did they win 43%?

THE ARITHMETIC
Each game's two prices are de-vigged into probabilities that sum to one, and
the team's own de-vigged probability is what the market claimed. Sum those
across all their games and you get the wins the market expected. Compare to the
wins they got.

  expected 34.1, actual 31   ->  the market was close
  expected 34.1, actual 45   ->  the market underrated them all season

WHY A PERMUTATION AND NOT A GUT CALL
Over 80 games a gap of three or four wins is ordinary. So the games are
re-simulated from the market's own probabilities thousands of times, and the
actual win count is placed in that distribution. A team that finishes outside
it was genuinely mispriced; a team inside it was priced correctly and just ran
hot or cold. This is a two-sided question - underrated and overrated both
count - so the p-value is two-sided.

ROI IS REPORTED ALONGSIDE, AND IS THE SAME FACT IN MONEY
If the market is right, backing them every game returns about minus the hold.
Much better or worse than that is the same finding as a calibration gap,
expressed in units, and the two should agree. When they disagree the cause is
almost always a few long prices carrying the ROI, which the buckets expose.

Writes output/team_calibration_<team>.md.
"""

from __future__ import annotations

import argparse
import logging
import random
import statistics as st
from pathlib import Path

from . import grade
from .pregame_money import _implied
from .team_at_odds import _rows

log = logging.getLogger("team_calibration")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 20000

BUCKETS = [("heavy favourite (−180 or shorter)", -10000, -180),
           ("clear favourite (−179 to −140)", -179, -140),
           ("slight favourite (−139 to −101)", -139, -101),
           ("slight dog (+100 to +139)", 100, 139),
           ("clear dog (+140 to +179)", 140, 179),
           ("big dog (+180 or longer)", 180, 10000)]


def _p(r: dict) -> float | None:
    """The team's de-vigged probability, i.e. what the market actually claimed."""
    tot = _implied(r["odds"]) + _implied(r["opp_odds"])
    return (_implied(r["odds"]) / tot) if tot > 0 else None


def _line(rs: list[dict]) -> str:
    w = sum(1 for r in rs if r["won"])
    exp = sum(_p(r) for r in rs)
    u = sum(grade.american_profit(r["odds"]) if r["won"] else -1 for r in rs)
    gap = w - exp
    return (f"| {len(rs)} | {exp:.1f} | {w} | **{gap:+.1f}** | "
            f"{u:+.2f}u ({u/len(rs):+.1%}) |")


def build(team: str) -> str:
    rows = [r for r in _rows(team) if _p(r) is not None]
    md = [f"# Has the market been right about {team}?", "",
          "_Each game's two prices are de-vigged into probabilities summing to "
          "one; the team's own share is what the market claimed. Add those up "
          "across every graded game and you get the wins the market expected — "
          "then compare to the wins they got._", "",
          f"- graded games with both prices: **{len(rows)}**", ""]
    if len(rows) < 30:
        return "\n".join(md + ["Too few games to calibrate.", ""])

    exp = sum(_p(r) for r in rows)
    act = sum(1 for r in rows if r["won"])

    md += ["## All season", "",
           "| games | market expected | actual wins | gap | flat-stake |",
           "|---|---|---|---|---|", _line(rows), ""]

    rng = random.Random(2029)
    ps = [_p(r) for r in rows]
    sim = [sum(1 for p in ps if rng.random() < p) for _ in range(TRIALS)]
    lo, hi = sorted(sim)[int(.025 * TRIALS)], sorted(sim)[int(.975 * TRIALS)]
    d = abs(act - exp)
    pv = (sum(1 for x in sim if abs(x - exp) >= d) + 1) / (TRIALS + 1)
    md += [f"- re-simulating these games from the market's own probabilities: "
           f"**{st.mean(sim):.1f} wins** on average, 95% of the time between "
           f"**{lo} and {hi}**",
           f"- they actually won **{act}**",
           f"- **two-sided p = {pv:.3f}**"]
    verdict = ("**inside** the range, so the market has been right about them "
               "and any gap is ordinary variance"
               if lo <= act <= hi else
               "**outside** the range, which is a real mispricing rather than "
               "a hot or cold run")
    md += [f"- that is {verdict}", ""]

    md += ["## By price, because a season average can hide both directions", "",
           "| price | games | expected | actual | gap | flat-stake |",
           "|---|---|---|---|---|---|"]
    for lab, blo, bhi in BUCKETS:
        sub = [r for r in rows if blo <= r["odds"] <= bhi]
        if sub:
            md.append(f"| {lab} " + _line(sub))
    md.append("")

    md += ["## Home and away", "", "| | games | expected | actual | gap | flat-stake |",
           "|---|---|---|---|---|---|"]
    for lab, sub in (("at home", [r for r in rows if r["home"]]),
                     ("on the road", [r for r in rows if not r["home"]])):
        if sub:
            md.append(f"| {lab} " + _line(sub))
    md.append("")

    md += ["## Reading it", "",
           "- **gap** is actual wins minus the wins the price implied. Near zero "
           "means the market had them right",
           "- a flat-stake return near **−4% to −5%** is what a correctly priced "
           "team looks like — that is the hold, not a failing",
           "- the buckets matter because a season-long gap of zero can be a team "
           "the market overrates as a favourite and underrates as a dog, which "
           "cancels in the total and is tradeable",
           f"- {len(rows)} games is one season. A gap needs to be large to mean "
           "anything at this sample size, which is what the simulated range is "
           "there to show", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("team")
    a = ap.parse_args()
    md = build(a.team)
    OUTPUT_DIR.mkdir(exist_ok=True)
    slug = a.team.split()[-1].lower()
    (OUTPUT_DIR / f"team_calibration_{slug}.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
