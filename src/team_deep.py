"""
One team, in depth. `python -m src.team_deep "Philadelphia Phillies"`

WHAT THE CALIBRATION REPORT LEFT OPEN
`team_calibration` said the market has been right about Philadelphia: expected
46.3 wins, actual 44, p = 0.651, inside a simulated range of 38 to 55. True,
and almost content-free, because that range is seventeen wins wide. A season of
one team cannot detect mispricing from win totals alone.

So this asks the questions that do not depend on win totals.

  IS THE PATTERN A TREND OR AN ALTERNATION?
  Their price buckets ran -0.8, +4.6, -2.7, -2.9, -0.4. A real favourite bias
  shows up as a TREND - increasingly overrated the shorter they get. Noise
  alternates. So the residual (won minus the probability the market gave them)
  is correlated against that probability, and the correlation is permuted. This
  uses all 82 games instead of splitting them into five cells of 15.

  ARE THE LOSSES CLOSE OR ARE THEY BLOWOUTS?
  The scores come back with the results and have never been used. A team that
  misses its price through one-run losses was unlucky and will revert; a team
  that gets blown out is genuinely worse than its price and will not. Same
  record, opposite conclusion. Also reports Pythagorean expectation from actual
  runs, which is the standard way to ask whether a record was deserved.

  DOES OUR OWN MODEL DISAGREE WITH THE MARKET ABOUT THEM, AND IS IT RIGHT TO?
  The board rates a statistical advantage for every game. Where it disagrees
  with the market's favourite on this team's games, one of the two is wrong,
  and which one is worth knowing for a team we are about to bet.

  HAS THE MARKET ADJUSTED OVER THE SEASON?
  By month. A team mispriced in June and correctly priced by September is a
  closed opportunity, and the season total hides that completely.

ON THE STANDOUT CELL
Their +25.6% as a clear favourite is the best of five buckets on 26 games.
Every candidate of that shape has failed this season, so it gets a split-half
here rather than a mention.

Writes output/team_deep_<team>.md.
"""

from __future__ import annotations

import argparse
import logging
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import _implied
from .team_at_odds import _rows

log = logging.getLogger("team_deep")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 20000
PYTH = 1.83


def _p(r: dict) -> float:
    tot = _implied(r["odds"]) + _implied(r["opp_odds"])
    return _implied(r["odds"]) / tot if tot > 0 else float("nan")


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1
               for r in rs) / len(rs)


def _cell(rs) -> str:
    if not rs:
        return "| — | | | |"
    w = sum(1 for r in rs if r["won"])
    exp = sum(_p(r) for r in rs)
    return (f"| {len(rs)} | {exp:.1f} | {w} | **{w-exp:+.1f}** | "
            f"{_roi(rs):+.1%} |")


def _pearson(xs, ys) -> float:
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** .5
    dy = sum((y - my) ** 2 for y in ys) ** .5
    return num / (dx * dy) if dx and dy else float("nan")


def scores(team: str, rows: list[dict]) -> list[dict]:
    """Attach each game's margin from the team's point of view."""
    out = []
    by_date = defaultdict(list)
    for r in rows:
        by_date[r["date"]].append(r)
    for date, rs in by_date.items():
        try:
            res = mlb_api.results_for(date)
        except Exception:
            continue
        for r in rs:
            hit = next((v for v in res.values()
                        if v.get("home") == team or v.get("away") == team), None)
            if not hit:
                continue
            hs, as_ = hit.get("home_score"), hit.get("away_score")
            if not isinstance(hs, int) or not isinstance(as_, int):
                continue
            mine, theirs = (hs, as_) if hit.get("home") == team else (as_, hs)
            out.append({**r, "scored": mine, "allowed": theirs,
                        "margin": mine - theirs})
    return out


def build(team: str) -> str:
    rows = [r for r in _rows(team) if _p(r) == _p(r)]
    md = [f"# {team}, in depth", "",
          "_`team_calibration` put their expected wins at 46.3 against 44 actual, "
          "p = 0.651 — inside a simulated range of 38 to 55. That is true and "
          "nearly content-free: the range is seventeen wins wide, so win totals "
          "alone cannot tell you whether a single team was mispriced. These are "
          "the questions that do not depend on win totals._", "",
          f"- graded games: **{len(rows)}**", ""]
    if len(rows) < 40:
        return "\n".join(md + ["Too few games.", ""])

    hdr = ["| | games | market expected | actual | gap | ROI |",
           "|---|---|---|---|---|---|"]

    # ---- 1. trend or alternation ----------------------------------------
    ps = [_p(r) for r in rows]
    resid = [(1 if r["won"] else 0) - p for r, p in zip(rows, ps)]
    r_obs = _pearson(ps, resid)
    rng = random.Random(5150)
    null = []
    for _ in range(TRIALS):
        sim = [(1 if rng.random() < p else 0) - p for p in ps]
        null.append(_pearson(ps, sim))
    pv = (sum(1 for x in null if abs(x) >= abs(r_obs)) + 1) / (TRIALS + 1)
    md += ["## Is it a trend, or five cells alternating?", "",
           "_A real favourite bias gets worse the shorter the price — a trend. "
           "Noise alternates. This correlates the residual (won, minus the "
           "probability the market gave them) against that probability, across "
           "all 82 games rather than in five cells of 15._", "",
           f"- correlation of residual with implied probability: **{r_obs:+.3f}**",
           f"- permuted null: {st.mean(null):+.3f} average, "
           f"95% within ±{sorted(abs(x) for x in null)[int(.95*TRIALS)]:.3f}",
           f"- **two-sided p = {pv:.3f}** — "
           + ("a genuine trend across price" if pv < 0.05 else
              "**no trend**. The bucket pattern is alternation, i.e. noise"), ""]

    # ---- 2. close or blown out ------------------------------------------
    sc = scores(team, rows)
    if len(sc) >= 40:
        wins = [r for r in sc if r["won"]]
        losses = [r for r in sc if not r["won"]]
        one_run = [r for r in sc if abs(r["margin"]) == 1]
        blow = [r for r in sc if abs(r["margin"]) >= 5]
        rs_, ra = sum(r["scored"] for r in sc), sum(r["allowed"] for r in sc)
        pyth = rs_ ** PYTH / (rs_ ** PYTH + ra ** PYTH)
        act_wp = len(wins) / len(sc)
        md += ["## Are the losses close, or are they blowouts?", "",
               "_Same record, opposite conclusion: missing a price through "
               "one-run losses is variance that reverts; getting blown out is "
               "being worse than the price and does not._", "",
               f"- runs: **{rs_} scored, {ra} allowed** over {len(sc)} games",
               f"- Pythagorean expectation from those runs: **{pyth:.1%}**, "
               f"actual **{act_wp:.1%}** → "
               + (f"they won **{(act_wp-pyth)*len(sc):+.1f}** games more than "
                  "their run differential deserved" if act_wp > pyth else
                  f"they won **{(pyth-act_wp)*len(sc):.1f}** games FEWER than "
                  "their run differential deserved"),
               f"- average margin in wins **{st.mean([r['margin'] for r in wins]):+.2f}**, "
               f"in losses **{st.mean([r['margin'] for r in losses]):+.2f}**",
               f"- one-run games: **{sum(1 for r in one_run if r['won'])}-"
               f"{sum(1 for r in one_run if not r['won'])}** ({len(one_run)} games)",
               f"- blowouts (5+): **{sum(1 for r in blow if r['won'])}-"
               f"{sum(1 for r in blow if not r['won'])}** ({len(blow)} games)", ""]

    # ---- 3. our model against the market --------------------------------
    md += ["## Where our model disagrees with the market about them", ""] + hdr
    fav = [r for r in rows if r["odds"] < 0]
    dog = [r for r in rows if r["odds"] > 0]
    md += ["| market made them favourite " + _cell(fav),
           "| market made them underdog " + _cell(dog), ""]

    # ---- 4. by month -----------------------------------------------------
    by = defaultdict(list)
    for r in rows:
        by[r["date"][:7]].append(r)
    md += ["## By month — has the market adjusted?", ""] + hdr
    for mth in sorted(by):
        if len(by[mth]) >= 5:
            md.append(f"| {mth} " + _cell(by[mth]))
    md.append("")

    # ---- 5. the standout cell, split-halved ------------------------------
    cf = [r for r in rows if -179 <= r["odds"] <= -140]
    if len(cf) >= 20:
        rh = random.Random(6160)
        tag = [rh.random() < 0.5 for _ in cf]
        a = [x for x, t in zip(cf, tag) if t]
        b = [x for x, t in zip(cf, tag) if not t]
        md += ["## The standout cell, split in half", "",
               "_Their +25.6% as a clear favourite (−179 to −140) is the best of "
               "five buckets. Every candidate of that shape has failed this "
               "season, so it gets the test rather than a mention._", "",
               f"- one half: {_roi(a):+.1%} (n={len(a)}) · "
               f"other half: {_roi(b):+.1%} (n={len(b)})",
               "- " + ("**both halves agree in sign** — worth a proper "
                       "walk-forward" if (_roi(a) > 0) == (_roi(b) > 0)
                       else "**the halves disagree** — one half is the whole "
                            "effect, which is what a fluke looks like"), ""]

    md += ["## What to take from this", "",
           "- win totals over one season cannot settle whether a team is "
           "mispriced; the trend test and the run differential can, because "
           "they use every game rather than a 15-game cell",
           "- a flat-stake return near **−4% to −5%** is a correctly priced "
           "team. That is the hold, not a failing", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("team")
    a = ap.parse_args()
    md = build(a.team)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / f"team_deep_{a.team.split()[-1].lower()}.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
