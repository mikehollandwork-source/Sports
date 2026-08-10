"""
Home underdog + hotter bats + stars producing + line moving against them.

THE HYPOTHESIS
A home dog whose offence is running hot, whose best bats are the ones producing,
and whose price is drifting longer - so the market is walking away from a team
that is actually playing well. Buy the discount.

WHY IT IS BUILT AS A FUNNEL
Four conditions stacked on 409 underdogs. Each one is a filter, and the whole
question is whether anything survives to a testable count. Reporting only the
final ROI would hide that, so this prints n and ROI after EVERY step - the
collapse is the finding as much as the number at the bottom.

THE POWER PROBLEM, STATED BEFORE THE RESULT
At small n a betting ROI is almost unmeasurable. One extra win on 15 games at
+150 swings ROI by ~16 points. So this also reports, for whatever n survives,
the 95% interval and the sample that WOULD be needed to distinguish a real +10%
edge from zero. A number without that context is decoration.

Definitions, all from data already on the board:
    home underdog     home team with a positive closing moneyline
    hotter bats       form.delta higher for the dog than the opponent
    stars producing   dog's hot bats are outproducing the opponent's, measured
                      as the SUM of their deltas
    line against      implied_shift moved AWAY from the dog

A NOTE ON "STARS PRODUCING", because the first version of it was wrong
The obvious definition - "the dog has at least as many hot bats" - is vacuous
here. `form.hot` is a fixed top-2 list, not a count of who happens to be hot, so
both teams carry two names in almost every game and the comparison is a tie that
resolves true. It passed 77 of 84 home dogs and left the funnel's third step
identical to its second. Summing the hot bats' deltas asks the intended question
- how much those bats are actually outperforming - and separates cleanly from
the team-wide delta: 11 games have hotter bats without star production, 7 the
reverse, 31 both.

Writes output/hot_home_dog.md.
"""

from __future__ import annotations

import glob
import json
import logging
import math
import random
import statistics as st
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import HOLDOUT_FROM, _implied

log = logging.getLogger("hot_home_dog")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MOVE_MIN = 0.01


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
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = matchup.split(" @ ")
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            if price.get(home) is None or price[home] <= 0:
                continue                      # home team is not the underdog
            dog, odds = home, price[home]

            form = g.get("form") or {}
            fh, fa = form.get("home") or {}, form.get("away") or {}
            dh, da = fh.get("delta"), fa.get("delta")
            if not isinstance(dh, (int, float)) or not isinstance(da, (int, float)):
                continue
            # sum of the top bats' deltas, not how many names are in the list
            hot_dog = sum(p.get("delta", 0) for p in (fh.get("hot") or []))
            hot_opp = sum(p.get("delta", 0) for p in (fa.get("hot") or []))

            shift = (pc.get("line_check") or {}).get("implied_shift")
            toward_dog = None
            if isinstance(shift, (int, float)):
                toward_dog = shift if dog == adv else -shift

            tot = _implied(a_ml) + _implied(o_ml)
            recs.append({
                "date": date, "dog": dog, "odds": odds,
                "won": res["winner"] == dog,
                "p": (_implied(odds) / tot) if tot > 0 else 0.5,
                "hotter_bats": dh > da,
                "stars": hot_dog > hot_opp,
                "line_against": (toward_dog is not None
                                 and toward_dog <= -MOVE_MIN),
            })
    return recs


def _stat(rows) -> tuple[int, int, float, float]:
    w = sum(1 for x in rows if x["won"])
    u = sum(grade.american_profit(x["odds"]) if x["won"] else -1 for x in rows)
    return w, len(rows) - w, u, (u / len(rows) if rows else 0.0)


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w, l, u, roi = _stat(rows)
    return f"{w}-{l} ({w/len(rows):.0%}) · {u:+.1f}u · **{roi:+.1%}** (n={len(rows)})"


def _boot_ci(rows, trials=4000) -> tuple[float, float]:
    if len(rows) < 5:
        return (float("nan"), float("nan"))
    rng = random.Random(41)
    out = []
    for _ in range(trials):
        s = [rows[rng.randrange(len(rows))] for _ in rows]
        out.append(_stat(s)[3])
    out.sort()
    return out[int(.025 * trials)], out[int(.975 * trials)]


def _needed_n(rows, edge=0.10) -> int:
    """Games needed to separate a real +10% ROI from zero at 95%/80% power."""
    if len(rows) < 5:
        return 0
    sd = st.pstdev([grade.american_profit(x["odds"]) if x["won"] else -1
                    for x in rows]) or 1.0
    return int(math.ceil(((1.96 + 0.84) * sd / edge) ** 2))


def build() -> str:
    recs = collect()
    md = ["# Hot home underdog with the line moving against it", "",
          "_Four conditions stacked. Each step's count is printed because the "
          "collapse is as much the answer as the final number._", ""]
    if not recs:
        return "\n".join(md + ["No home underdogs with form data.", ""])

    steps = [
        ("home underdogs (with form data)", lambda r: True),
        ("+ hotter bats than opponent", lambda r: r["hotter_bats"]),
        ("+ stars producing", lambda r: r["hotter_bats"] and r["stars"]),
        ("+ line moving against them", lambda r: r["hotter_bats"] and r["stars"]
         and r["line_against"]),
    ]
    md += ["## The funnel", "", "| step | surviving | backing them |", "|---|---|---|"]
    final = recs
    for label, test in steps:
        sub = [r for r in recs if test(r)]
        md.append(f"| {label} | **{len(sub)}** | {_fmt(sub)} |")
        final = sub
    md.append("")

    # each condition on its own, so a stack that fails shows WHICH part fails
    md += ["## Each condition alone", "", "| condition | backing them |", "|---|---|",
           f"| hotter bats | {_fmt([r for r in recs if r['hotter_bats']])} |",
           f"| stars producing | {_fmt([r for r in recs if r['stars']])} |",
           f"| line against | {_fmt([r for r in recs if r['line_against']])} |",
           f"| all home dogs | {_fmt(recs)} |", ""]

    # the two form conditions have to be shown to be distinct, because the
    # first version of "stars producing" was a tie-resolving no-op
    both = sum(1 for r in recs if r["hotter_bats"] and r["stars"])
    md += [f"_Overlap of the two form conditions: "
           f"{sum(1 for r in recs if r['hotter_bats'] and not r['stars'])} bats "
           f"only, {sum(1 for r in recs if r['stars'] and not r['hotter_bats'])} "
           f"stars only, {both} both. They are measuring different things._", ""]

    md += ["## What the final cell can and cannot tell you", ""]
    if len(final) < 5:
        md += [f"Only **{len(final)}** games survive all four conditions. That is "
               "not a sample - it is an anecdote. No ROI computed.", ""]
        return "\n".join(md)

    lo, hi = _boot_ci(final)
    need = _needed_n(final, 0.10)
    w, l, u, roi = _stat(final)
    pre = [r for r in final if r["date"] < HOLDOUT_FROM]
    post = [r for r in final if r["date"] >= HOLDOUT_FROM]
    md += [f"- final cell: {_fmt(final)}",
           f"- 95% bootstrap interval: **{lo:+.1%} to {hi:+.1%}** "
           f"(width {hi-lo:.0%} points)",
           f"- in-sample: {_fmt(pre)}", f"- holdout: {_fmt(post)}",
           f"- **games needed to distinguish a real +10% edge from zero: "
           f"~{need}**", ""]
    swing = (grade.american_profit(st.median([x["odds"] for x in final])) + 1) / len(final)
    md += [f"_One extra win here moves ROI by about **{swing:.0%} points**. "
           "Any conclusion drawn from this cell is a conclusion about one or two "
           "games._", ""]
    md.append("_Stacking filters on a fixed dataset always finds a subset that "
              "looks good; the underdog scan's best of 64 cells matched the "
              "noise median almost exactly. The interval above is the honest "
              "read, not the point estimate._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "hot_home_dog.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
