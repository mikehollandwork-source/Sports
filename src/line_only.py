"""
Line movement alone: back the side the line moved AGAINST, at every threshold
and every closing-price bucket.

THE RULE UNDER TEST
No handle, no tickets, no order book, no stat model. For every game the line
moved on, back the side whose price got LONGER - the side money is leaving. That
is "the line moved against us" with "us" defined by the movement itself rather
than by any of our other signals.

    line_check.implied_shift is signed toward advantage_team, so:
        shift > 0  -> moved toward advantage  -> back the OPPONENT
        shift < 0  -> moved toward opponent   -> back the ADVANTAGE side

Prices are the board's captured moneylines, which _lock_started_games freezes at
first pitch - so they are closing prices, not live ones.

WHAT IS SWEPT
  * five move thresholds, from 0.5% to 5% of implied probability
  * five closing-price buckets, heavy favourite through heavy underdog
  * favourites and underdogs reported separately as well as pooled

THE CORRECTION THAT DECIDES IT
Five thresholds x six price groupings is a thirty-cell grid, and this session has
established what a grid that size produces from noise: the underdog scan's best
cell landed at +18.7% against a noise median of +18.6%. So the headline is not
the best cell but a max-statistic permutation - outcomes redrawn from de-vigged
closing prices, every cell recomputed, the best recorded, repeated. A cell only
means something if it beats what the search itself manufactures.

Writes output/line_only.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import HOLDOUT_FROM, _implied

log = logging.getLogger("line_only")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MIN_CELL = 25
TRIALS = 2000

THRESHOLDS = [0.005, 0.01, 0.02, 0.03, 0.05]
# closing american odds of the side we back
PRICE_BUCKETS = [
    ("heavy fav (<= -200)", lambda o: o <= -200),
    ("mod fav (-199..-130)", lambda o: -199 <= o <= -130),
    ("slight fav (-129..-101)", lambda o: -129 <= o <= -101),
    ("slight dog (+100..+139)", lambda o: 100 <= o <= 139),
    ("mod/heavy dog (>= +140)", lambda o: o >= 140),
]


def collect() -> list[dict]:
    recs = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for g in json.loads(Path(f).read_text()).get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            matchup = g.get("matchup") or ""
            if " @ " not in matchup:
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            shift = (pc.get("line_check") or {}).get("implied_shift")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            if not isinstance(shift, (int, float)) or shift == 0:
                continue
            away, home = matchup.split(" @ ")
            opp = home if adv == away else away
            # back the side the line moved AWAY from
            bet, odds = ((opp, o_ml) if shift > 0 else (adv, a_ml))
            tot = _implied(a_ml) + _implied(o_ml)
            recs.append({
                "date": date, "bet": bet, "odds": odds,
                "won": res["winner"] == bet,
                "move": abs(shift),
                "p": (_implied(odds) / tot) if tot > 0 else 0.5,
                "is_dog": odds > 0,
            })
    return recs


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w = sum(1 for x in rows if x["won"])
    u = sum(grade.american_profit(x["odds"]) if x["won"] else -1 for x in rows)
    tag = "" if len(rows) >= MIN_CELL else " _(thin)_"
    return (f"{w}-{len(rows)-w} ({w/len(rows):.0%}) · {u:+.1f}u · "
            f"**{u/len(rows):+.1%}** (n={len(rows)}){tag}")


def _roi(rows, wins=None) -> float:
    if not rows:
        return 0.0
    u = 0.0
    for i, x in enumerate(rows):
        won = x["won"] if wins is None else wins[x["_i"]]
        u += grade.american_profit(x["odds"]) if won else -1
    return u / len(rows)


def build() -> str:
    recs = collect()
    for i, r in enumerate(recs):
        r["_i"] = i
    md = ["# Line movement alone — back the side the line moved against", "",
          "_No handle, no tickets, no order book, no stat model. For every game "
          "the line moved on, back the side whose price got longer. Prices are "
          "the board's closing moneylines, frozen at first pitch._", "",
          f"- games with a non-zero line move: **{len(recs)}**", ""]
    if len(recs) < MIN_CELL:
        return "\n".join(md + ["Too few games.", ""])

    md += ["## Baseline — every game with any move", "",
           f"- {_fmt(recs)}",
           f"- as a favourite: {_fmt([r for r in recs if not r['is_dog']])}",
           f"- as a dog: {_fmt([r for r in recs if r['is_dog']])}", ""]

    # ---- threshold sweep ----
    md += ["## By size of the move", "",
           "| min move | all | favourites | dogs |", "|---|---|---|---|"]
    for t in THRESHOLDS:
        sub = [r for r in recs if r["move"] >= t]
        md.append(f"| ≥{t:.1%} | {_fmt(sub)} | "
                  f"{_fmt([r for r in sub if not r['is_dog']])} | "
                  f"{_fmt([r for r in sub if r['is_dog']])} |")
    md.append("")

    # ---- grid: threshold x closing price ----
    cells: dict = {}
    md += ["## By move size and closing price", "",
           "| min move | " + " | ".join(lbl for lbl, _ in PRICE_BUCKETS) + " |",
           "|---" * (len(PRICE_BUCKETS) + 1) + "|"]
    for t in THRESHOLDS:
        row = [f"| ≥{t:.1%} "]
        for lbl, test in PRICE_BUCKETS:
            sub = [r for r in recs if r["move"] >= t and test(r["odds"])]
            if len(sub) >= MIN_CELL:
                cells[f"≥{t:.1%} / {lbl}"] = sub
            row.append(f"| {_fmt(sub)} ")
        md.append("".join(row) + "|")
    md.append("")

    # ---- the correction ----
    if cells:
        best_label, best_rows = max(cells.items(), key=lambda kv: _roi(kv[1]))
        best = _roi(best_rows)
        rng = random.Random(31)
        null_max = []
        for _ in range(TRIALS):
            w = [rng.random() < r["p"] for r in recs]
            null_max.append(max(_roi(rows, w) for rows in cells.values()))
        beats = sum(1 for m in null_max if m >= best)
        null_max.sort()
        md += ["## Does the best cell beat the search itself?", "",
               f"- cells at n≥{MIN_CELL}: **{len(cells)}**",
               f"- best cell: `{best_label}` at **{best:+.1%}**",
               f"- median best-in-noise: **{st.median(null_max):+.1%}**",
               f"- 95th percentile of best-in-noise: **{null_max[int(.95*TRIALS)]:+.1%}**",
               f"- **corrected p = {beats/TRIALS:.3f}**", ""]
        md += (["**Clears the bar.** Better than a grid this size finds in noise.", ""]
               if beats / TRIALS <= 0.05 else
               ["**Does not clear.** A grid this size produces a cell this good "
                "from noise more than 5% of the time, so the number is the "
                "search talking, not the data.", ""])

        pre = [r for r in best_rows if r["date"] < HOLDOUT_FROM]
        post = [r for r in best_rows if r["date"] >= HOLDOUT_FROM]
        md += [f"- best cell in-sample: {_fmt(pre)}",
               f"- best cell holdout: {_fmt(post)}", ""]

    md.append("_Every cell here shares one dataset, so reading the grid for the "
              "greenest number is the same mistake the underdog scan made - "
              "there the best of 64 cells matched the noise median almost "
              "exactly._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "line_only.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
