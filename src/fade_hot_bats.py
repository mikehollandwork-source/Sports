"""
Fade the hot-bats team when the line is moving against it — swept by price.

THE HYPOTHESIS, GENERALISED
`hot_home_dog` asked whether a home dog with hot bats and a drifting price is a
buy. It is not: -29.4% on n=18. This asks the same question from the other
side and without the home-dog restriction: when a team's bats are hot and the
market is walking AWAY from them anyway, is the market right? Back the opponent.

WHY DROP "HOME DOG"
Because it costs 90% of the sample and the hypothesis does not need it. If the
market is correctly fading hot-bat teams, that is a fact about hot-bat teams,
not about which dugout they occupy. Restricting to home dogs took n to 18, where
one game moves ROI 12 points and the power calculation said ~781 games would be
needed. Generalising takes the same idea to the full board. The home-dog subset
is then a CONSISTENCY CHECK at the bottom, not the headline - a real effect
should survive the restriction, not depend on it.

THE CONFOUND THIS EXISTS TO ISOLATE
The proposal is "take the favourite at -130 or cheaper". Cheap favourites win
about 57% of the time, so ANY rule that ends up on cheap favourites will show a
respectable hit rate, whether or not hot bats have anything to do with it. So
every cell here is reported against a CONTROL: backing the favourite at the same
price, in every game, ignoring form and line movement entirely. The number that
matters is not the cell's ROI. It is the cell MINUS the control. If fading hot
bats adds nothing over "bet cheap favourites", the difference is zero and the
signal is the price bucket, not the bats.

The first version of that control was wrong, and wrong in the direction that
flatters the result: it filtered the fade-the-hot-side rows, which are already
form-selected, so it isolated the line-movement condition and left the cheap-
favourite confound entirely unmeasured while the report claimed otherwise. Two
controls are now carried - `fade-only` (drops the line filter) and `price-only`
(the favourite in every game, no form, no line) - and every corrected statistic
scores against `price-only`, the one the proposal actually needs.

"-130 OR LESS" IS AMBIGUOUS AND BOTH READINGS ARE SWEPT
It can mean "no worse than -130" (-100..-130, cheap favourites) or "-130 and
longer" (-130..-300, real favourites). The threshold sweep covers both, which is
the point: a single cutoff cannot be evaluated, only a curve can. A real effect
degrades gracefully either side of its optimum. The +40% dog signal was killed
by exactly this test - negative at 55%, peak at 70%, inverted at 80%.

PRE-REGISTERED BAR, WRITTEN BEFORE THE RESULT WAS SEEN
A cell is promotable only if ALL of these hold:
  1. n >= 100 in the cell
  2. plateau: three adjacent thresholds all positive, not a lone spike
  3. corrected p <= 0.05 against the max-statistic null over the sweep
  4. holdout (>= 2026-07-23) positive
  5. edge over the price-only control has a bootstrap CI excluding zero
Anything less is recorded and not shipped. Five have been missed before; this
is the sixth statement of the same bar.

Writes output/fade_hot_bats.md.
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

log = logging.getLogger("fade_hot_bats")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MOVE_MIN = 0.01
TRIALS = 4000
MIN_CELL = 30

# Upper bound on the price we are willing to pay for the fade side. "-130 or
# less" in both of its readings lives inside this sweep.
CEILINGS = [-110, -120, -130, -140, -150, -175, -200, -250]


def collect() -> list[dict]:
    """One row per game that has form on both sides, both prices, and a move."""
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

            form = g.get("form") or {}
            fh, fa = form.get("home") or {}, form.get("away") or {}
            dh, da = fh.get("delta"), fa.get("delta")
            if not isinstance(dh, (int, float)) or not isinstance(da, (int, float)):
                continue
            if dh == da:
                continue
            hot = home if dh > da else away
            cold = away if hot == home else home

            # sum of the top bats' deltas - the count is a fixed top-2 list and
            # comparing counts is a tie that resolves true (see hot_home_dog)
            sh = sum(p.get("delta", 0) for p in (fh.get("hot") or []))
            sa = sum(p.get("delta", 0) for p in (fa.get("hot") or []))
            stars_hot = (sh > sa) if hot == home else (sa > sh)

            shift = (pc.get("line_check") or {}).get("implied_shift")
            if not isinstance(shift, (int, float)):
                continue
            toward_hot = shift if hot == adv else -shift

            tot = _implied(a_ml) + _implied(o_ml)
            # The pure price control: the favourite in this game, chosen with no
            # reference to form or line movement at all. Kept per row so the
            # "cheap favourites win anyway" confound can be priced directly.
            fav = adv if a_ml < o_ml else opp
            recs.append({
                "date": date,
                "fav_odds": price[fav], "fav_won": res["winner"] == fav,
                "bet": cold, "odds": price[cold],       # we back the COLD side
                "won": res["winner"] == cold,
                "p": (_implied(price[cold]) / tot) if tot > 0 else 0.5,
                "fav_is_cold": fav == cold,
                "line_against_hot": toward_hot <= -MOVE_MIN,
                "stars_hot": stars_hot,
                "hot_is_home": hot == home,
                "hot_is_dog": price[hot] > 0,
                "form_gap": abs(dh - da),
            })
    return recs


def _stat(rows, wins=None) -> tuple[int, int, float, float]:
    """`wins` is indexed by game and always means 'the COLD side won', so a view
    holding the other side of the same game carries invert=True. Redrawing one
    winner per game keeps the two views consistent under permutation instead of
    letting both sides of a game win."""
    w = u = 0
    for x in rows:
        if wins is None:
            won = x["won"]
        else:
            won = wins[x["_i"]]
            if x.get("invert"):
                won = not won
        w += 1 if won else 0
        u += grade.american_profit(x["odds"]) if won else -1
    return w, len(rows) - w, u, (u / len(rows) if rows else 0.0)


def _fav_view(rows) -> list[dict]:
    """The favourite in each game, picked with no reference to form or the line.
    This is the 'cheap favourites win anyway' control the -130 proposal needs."""
    return [{"_i": r["_i"], "odds": r["fav_odds"], "won": r["fav_won"],
             "invert": not r["fav_is_cold"]} for r in rows]


def _roi(rows, wins=None) -> float:
    return _stat(rows, wins)[3]


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w, l, u, roi = _stat(rows)
    tag = "" if len(rows) >= MIN_CELL else " _(thin)_"
    return f"{w}-{l} ({w/len(rows):.0%}) · {u:+.1f}u · **{roi:+.1%}** (n={len(rows)}){tag}"


def _boot_diff(cell, control, trials=3000) -> tuple[float, float]:
    """CI on (cell ROI - control ROI). Resampled independently: the control is a
    superset, so this is deliberately conservative about the overlap."""
    if len(cell) < 5 or len(control) < 5:
        return (float("nan"), float("nan"))
    rng = random.Random(67)
    out = []
    for _ in range(trials):
        a = [cell[rng.randrange(len(cell))] for _ in cell]
        b = [control[rng.randrange(len(control))] for _ in control]
        out.append(_roi(a) - _roi(b))
    out.sort()
    return out[int(.025 * trials)], out[int(.975 * trials)]


def _needed_n(rows, edge=0.10) -> int:
    if len(rows) < 5:
        return 0
    sd = st.pstdev([grade.american_profit(x["odds"]) if x["won"] else -1
                    for x in rows]) or 1.0
    return int(math.ceil(((1.96 + 0.84) * sd / edge) ** 2))


def build() -> str:
    recs = collect()
    for i, r in enumerate(recs):
        r["_i"] = i

    md = ["# Fade the hot-bats team when the line moves against it", "",
          "_Back the side whose bats are COLDER, when the market is already "
          "walking away from the hotter side. Swept by the price of the side we "
          "back, because a single cutoff cannot be evaluated - only a curve "
          "can._", "",
          f"- games with form on both sides, both prices and a line move: "
          f"**{len(recs)}**", ""]
    if len(recs) < MIN_CELL:
        return "\n".join(md + ["Too few games.", ""])

    qual = [r for r in recs if r["line_against_hot"]]
    md += ["## The two populations", "",
           f"- every game (fade the hotter bats regardless of the line): "
           f"{_fmt(recs)}",
           f"- **line also moving against the hot side**: {_fmt(qual)}", ""]

    # ---- the sweep, each cell against its own same-price control ----
    md += ["## By price of the side we back", "",
           "Two controls, because they answer different questions. **Fade-only** "
           "drops the line-movement requirement, so the gap to it is what the "
           "line filter adds. **Price-only** backs the favourite at that price "
           "in every game with no reference to form or the line at all - it is "
           "literally \"just bet cheap favourites\", and the gap to IT is the "
           "only number that is about hot bats.", "",
           "| we pay no worse than | qualifying cell | fade-only | price-only "
           "(the confound) | edge vs price-only |", "|---|---|---|---|---|"]
    cells: dict = {}
    fade_ctl: dict = {}
    price_ctl: dict = {}
    for c in CEILINGS:
        sub = [r for r in qual if c <= r["odds"] < 0]
        fc = [r for r in recs if c <= r["odds"] < 0]
        pc_ = [r for r in _fav_view(recs) if c <= r["odds"] < 0]
        if len(sub) >= MIN_CELL:
            cells[f"{c}"] = sub
            fade_ctl[f"{c}"] = fc
            price_ctl[f"{c}"] = pc_
        edge = (_roi(sub) - _roi(pc_)) if sub and pc_ else 0.0
        md.append(f"| {c} or cheaper | {_fmt(sub)} | {_fmt(fc)} | {_fmt(pc_)} | "
                  f"**{edge:+.1%}** |")
    md.append("")

    if not cells:
        md += [f"No price bucket reaches n={MIN_CELL}. Nothing testable.", ""]
        return "\n".join(md)

    # ---- plateau or spike ----
    seq = [(c, _roi(cells[c]) - _roi(price_ctl[c])) for c in
           (str(x) for x in CEILINGS) if c in cells]
    runs, best_run = 0, 0
    for _, e in seq:
        runs = runs + 1 if e > 0 else 0
        best_run = max(best_run, runs)
    md += ["## Plateau or spike?", "",
           f"- longest run of adjacent thresholds with a positive edge: "
           f"**{best_run}** of {len(seq)}",
           "- a real effect degrades gracefully either side of its optimum; a "
           "lone positive surrounded by negatives is the shape that killed the "
           "+40% dog signal.", ""]

    # ---- max-statistic correction over the sweep ----
    best_label = max(cells, key=lambda k: _roi(cells[k]) - _roi(price_ctl[k]))
    best_rows = cells[best_label]
    best_edge = _roi(best_rows) - _roi(price_ctl[best_label])
    rng = random.Random(71)
    null_max = []
    for _ in range(TRIALS):
        w = [rng.random() < r["p"] for r in recs]
        null_max.append(max(_roi(cells[k], w) - _roi(price_ctl[k], w)
                            for k in cells))
    beats = sum(1 for m in null_max if m >= best_edge)
    null_max.sort()
    md += ["## Does the best threshold beat the sweep itself?", "",
           f"- thresholds at n>={MIN_CELL}: **{len(cells)}**",
           f"- best: `{best_label} or cheaper` at an edge of **{best_edge:+.1%}** "
           f"over price-only (its own ROI is {_roi(best_rows):+.1%})",
           f"- median best-edge in noise: **{st.median(null_max):+.1%}**",
           f"- 95th percentile in noise: **{null_max[int(.95*TRIALS)]:+.1%}**",
           f"- **corrected p = {beats/TRIALS:.3f}**", ""]
    md += (["**Clears the bar.**", ""] if beats / TRIALS <= 0.05 else
           ["**Does not clear.** A sweep this size produces an edge this good "
            "from noise more than 5% of the time.", ""])

    lo, hi = _boot_diff(best_rows, price_ctl[best_label])
    pre = [r for r in best_rows if r["date"] < HOLDOUT_FROM]
    post = [r for r in best_rows if r["date"] >= HOLDOUT_FROM]
    md += [f"- edge CI vs price-only control: **{lo:+.1%} to {hi:+.1%}**",
           f"- in-sample: {_fmt(pre)}", f"- holdout: {_fmt(post)}",
           f"- games needed to call a real +10% edge: ~**{_needed_n(best_rows)}**",
           ""]

    # ---- the pre-registered bar, scored ----
    checks = [
        (f"n >= 100 in the cell (n={len(best_rows)})", len(best_rows) >= 100),
        (f"plateau of >= 3 adjacent thresholds (longest={best_run})", best_run >= 3),
        (f"corrected p <= 0.05 (p={beats/TRIALS:.3f})", beats / TRIALS <= 0.05),
        (f"holdout positive ({_roi(post):+.1%})", bool(post) and _roi(post) > 0),
        (f"edge CI excludes zero ({lo:+.1%}..{hi:+.1%})", lo > 0),
    ]
    md += ["## Scored against the pre-registered bar", "",
           "| requirement | met |", "|---|---|"]
    for label, ok in checks:
        md.append(f"| {label} | {'✅' if ok else '❌'} |")
    md += ["", ("**PROMOTABLE** — all five met." if all(o for _, o in checks)
                else "**NOT promotable.** Recorded, not shipped."), ""]

    # ---- consistency checks: does it need the extra conditions? ----
    md += ["## Consistency — does the effect need the trimmings?", "",
           "| subset of the best cell | backing the cold side |", "|---|---|",
           f"| all of it | {_fmt(best_rows)} |",
           f"| hot side was the home team | "
           f"{_fmt([r for r in best_rows if r['hot_is_home']])} |",
           f"| hot side was a home dog (the original cell) | "
           f"{_fmt([r for r in best_rows if r['hot_is_home'] and r['hot_is_dog']])} |",
           f"| hot side's stars also outproducing | "
           f"{_fmt([r for r in best_rows if r['stars_hot']])} |",
           f"| form gap in the top half | "
           f"{_fmt([r for r in best_rows if r['form_gap'] >= st.median([x['form_gap'] for x in best_rows])])} |",
           "",
           "_A real effect should survive these restrictions, not depend on "
           "them. If it only appears in one sliver, that sliver is the search "
           "talking._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "fade_hot_bats.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
