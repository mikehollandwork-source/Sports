"""
BvP and the stat-edge margin: separately, combined, and crossed with the line.

WHAT IS BEING TESTED
Two of the model's oldest inputs, measured directly against results for the
first time:

  margin    `components.stat_edge.margin` - how far apart the two teams'
            statistical-advantage scores are. `advantage_team` names the side.
  bvp       batter-vs-pitcher history for the probable starter, and `bvp_pen`
            the same against the bullpen. Each names an `edge_team` and a `gap`.

Backing `advantage_team` at every margin IS the stat model betting itself, so
the baseline row is the answer to a question this system has never asked
plainly: does the model beat the market? Everything else is conditioning on top
of that.

THE GRID, AND WHY THE HEADLINE IS NOT THE BEST CELL
Three signals x five thresholds each, agree/disagree splits, and a line-movement
cross in both directions is well over a hundred cells. This session has measured
what a grid that size manufactures: the 64-cell underdog scan's best cell landed
+18.7% against a noise median of +18.6%, and a price sweep last run produced a
+15.1% edge that fell to +5.1% once its control was fixed. So every cell at
n>=MIN_CELL enters one max-statistic permutation, outcomes redrawn from de-vigged
closing prices, and the reported p is corrected for the whole search.

DIRECTION IS PART OF THE TEST, NOT A FREE PARAMETER
Line movement is crossed BOTH ways - toward the pick and against it - because
picking the direction after seeing the numbers is how a 50/50 choice becomes a
"finding". Both are reported at every threshold.

PRE-REGISTERED BAR
  1. n >= 100 in the cell
  2. plateau: >= 3 adjacent thresholds positive, not a lone spike
  3. corrected p <= 0.05 against the max-statistic null
  4. holdout (>= 2026-07-23) positive
  5. beats the back-advantage_team baseline, not just zero
Anything less is recorded, not shipped.

Writes output/bvp_margin.md.
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

log = logging.getLogger("bvp_margin")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 3000
MIN_CELL = 40

MARGIN_STEPS = [0.0, 0.10, 0.20, 0.30, 0.50]
GAP_STEPS = [0.0, 0.04, 0.08, 0.14, 0.25]
LINE_STEPS = [0.005, 0.01, 0.02, 0.03]


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
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            margin = ((pc.get("components") or {}).get("stat_edge") or {}).get("margin")
            if not isinstance(margin, (int, float)):
                continue

            b, bp = g.get("bvp") or {}, g.get("bvp_pen") or {}
            shift = (pc.get("line_check") or {}).get("implied_shift")
            tot = _implied(a_ml) + _implied(o_ml)
            recs.append({
                "date": date,
                "adv_odds": a_ml, "opp_odds": o_ml,
                "adv_won": res["winner"] == adv,
                "p_adv": (_implied(a_ml) / tot) if tot > 0 else 0.5,
                "margin": abs(margin),
                # None when the signal has no read on this game
                "bvp_adv": (b.get("edge_team") == adv) if b.get("edge_team") else None,
                "bvp_gap": b.get("gap") if isinstance(b.get("gap"), (int, float)) else None,
                "bvp_meaningful": bool(b.get("meaningful")),
                "pen_adv": (bp.get("edge_team") == adv) if bp.get("edge_team") else None,
                "pen_gap": bp.get("gap") if isinstance(bp.get("gap"), (int, float)) else None,
                # signed toward advantage_team
                "shift": shift if isinstance(shift, (int, float)) else None,
            })
    return recs


# --- views: a bet is always "which side of this game", so the permutation can
# --- redraw one winner per game and flip it for the opposing side.
def view_adv(rows) -> list[dict]:
    return [{"_i": r["_i"], "odds": r["adv_odds"], "won": r["adv_won"],
             "invert": False} for r in rows]


def view_side(rows, key) -> list[dict]:
    """Back the team named by `key` (True = advantage side, False = opponent)."""
    out = []
    for r in rows:
        if r[key] is None:
            continue
        on_adv = r[key]
        out.append({"_i": r["_i"],
                    "odds": r["adv_odds"] if on_adv else r["opp_odds"],
                    "won": r["adv_won"] if on_adv else not r["adv_won"],
                    "invert": not on_adv})
    return out


def _stat(rows, wins=None) -> tuple[int, int, float, float]:
    w = u = 0
    for x in rows:
        if wins is None:
            won = x["won"]
        else:
            won = wins[x["_i"]]
            if x["invert"]:
                won = not won
        w += 1 if won else 0
        u += grade.american_profit(x["odds"]) if won else -1
    return w, len(rows) - w, u, (u / len(rows) if rows else 0.0)


def _roi(rows, wins=None) -> float:
    return _stat(rows, wins)[3]


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w, l, u, roi = _stat(rows)
    tag = "" if len(rows) >= MIN_CELL else " _(thin)_"
    return f"{w}-{l} ({w/len(rows):.0%}) · {u:+.1f}u · **{roi:+.1%}** (n={len(rows)}){tag}"


def _flip(rows, recs) -> list[dict]:
    """The opposite side of every bet in a cell, at the opposite side's real
    price - so an inverted rule still pays the vig instead of assuming that a
    -X% cell becomes +X% backwards."""
    out = []
    for x in rows:
        r = recs[x["_i"]]
        on_adv = x["invert"]          # was backing the opponent -> now the adv
        out.append({"_i": x["_i"],
                    "odds": r["adv_odds"] if on_adv else r["opp_odds"],
                    "won": r["adv_won"] if on_adv else not r["adv_won"],
                    "invert": not on_adv})
    return out


def _toward(r, on_adv: bool):
    """Signed line movement toward the side we are backing."""
    if r["shift"] is None:
        return None
    return r["shift"] if on_adv else -r["shift"]


def build() -> str:
    recs = collect()
    for i, r in enumerate(recs):
        r["_i"] = i
    md = ["# BvP and stat-edge margin — alone, combined, and against the line", "",
          f"- graded games with a price and a margin: **{len(recs)}**", ""]
    if len(recs) < MIN_CELL:
        return "\n".join(md + ["Too few games.", ""])

    cells: dict = {}

    def cell(label, rows):
        if len(rows) >= MIN_CELL:
            cells[label] = rows
        return _fmt(rows)

    # ---- baselines ----
    base = view_adv(recs)
    md += ["## Baselines — the model betting itself", "",
           "| what | result |", "|---|---|",
           f"| back `advantage_team`, every game | {cell('base:adv', base)} |",
           f"| back the BvP `edge_team` | {cell('base:bvp', view_side(recs, 'bvp_adv'))} |",
           f"| back the bullpen-BvP `edge_team` | {cell('base:pen', view_side(recs, 'pen_adv'))} |",
           "",
           "_This is the number the whole board rests on. Every cell below has "
           "to beat it, not merely beat zero._", ""]
    baseline = _roi(base)

    # ---- margin alone ----
    md += ["## Margin alone (backing `advantage_team`)", "",
           "| min margin | result |", "|---|---|"]
    for t in MARGIN_STEPS:
        sub = view_adv([r for r in recs if r["margin"] >= t])
        md.append(f"| ≥{t:.2f} | {cell(f'margin>={t}', sub)} |")
    md.append("")

    # ---- bvp alone ----
    md += ["## BvP alone (backing the BvP `edge_team`)", "",
           "| min gap | starter BvP | bullpen BvP |", "|---|---|---|"]
    for t in GAP_STEPS:
        s = view_side([r for r in recs
                       if r["bvp_gap"] is not None and r["bvp_gap"] >= t], "bvp_adv")
        p = view_side([r for r in recs
                       if r["pen_gap"] is not None and r["pen_gap"] >= t], "pen_adv")
        md.append(f"| ≥{t:.2f} | {cell(f'bvp>={t}', s)} | {cell(f'pen>={t}', p)} |")
    md.append(f"\n_BvP flagged `meaningful`_: "
              f"{cell('bvp:meaningful', view_side([r for r in recs if r['bvp_meaningful']], 'bvp_adv'))}\n")

    # ---- combined ----
    agree = [r for r in recs if r["bvp_adv"] is True]
    disagree = [r for r in recs if r["bvp_adv"] is False]
    md += ["## Combined — does BvP agree with the margin?", "",
           "| case | backing `advantage_team` |", "|---|---|",
           f"| BvP agrees | {cell('agree', view_adv(agree))} |",
           f"| BvP disagrees | {cell('disagree', view_adv(disagree))} |",
           f"| BvP disagrees — back the BvP side instead | "
           f"{cell('disagree:bvp', view_side(disagree, 'bvp_adv'))} |", "",
           "### Agreement, swept on both thresholds", "",
           "| min margin | " + " | ".join(f"gap ≥{t:.2f}" for t in GAP_STEPS) + " |",
           "|---" * (len(GAP_STEPS) + 1) + "|"]
    for m in MARGIN_STEPS:
        row = [f"| ≥{m:.2f} "]
        for gp in GAP_STEPS:
            sub = view_adv([r for r in agree if r["margin"] >= m
                            and (r["bvp_gap"] or 0) >= gp])
            row.append(f"| {cell(f'agree:m>={m}:g>={gp}', sub)} ")
        md.append("".join(row) + "|")
    md.append("")

    # ---- line movement cross, both directions ----
    md += ["## Crossed with line movement", "",
           "Both directions at every threshold, because choosing the direction "
           "after seeing the numbers turns a coin flip into a \"finding\".", "",
           "| min move | agree + line TOWARD us | agree + line AGAINST us |",
           "|---|---|---|"]
    for t in LINE_STEPS:
        tow = view_adv([r for r in agree
                        if (_toward(r, True) or 0) >= t])
        agn = view_adv([r for r in agree
                        if (_toward(r, True) or 0) <= -t])
        md.append(f"| ≥{t:.1%} | {cell(f'agree:tow>={t}', tow)} | "
                  f"{cell(f'agree:agn>={t}', agn)} |")
    md.append("")
    md += ["| min move | margin≥0.30 + TOWARD | margin≥0.30 + AGAINST |",
           "|---|---|---|"]
    for t in LINE_STEPS:
        hi = [r for r in recs if r["margin"] >= 0.30]
        tow = view_adv([r for r in hi if (_toward(r, True) or 0) >= t])
        agn = view_adv([r for r in hi if (_toward(r, True) or 0) <= -t])
        md.append(f"| ≥{t:.1%} | {cell(f'm30:tow>={t}', tow)} | "
                  f"{cell(f'm30:agn>={t}', agn)} |")
    md.append("")

    # ---- the correction over everything above ----
    best_label = max(cells, key=lambda k: _roi(cells[k]))
    best_rows = cells[best_label]
    best = _roi(best_rows)
    rng = random.Random(83)
    null_max = []
    for _ in range(TRIALS):
        w = [rng.random() < r["p_adv"] for r in recs]
        null_max.append(max(_roi(v, w) for v in cells.values()))
    beats = sum(1 for m in null_max if m >= best) / TRIALS
    null_max.sort()
    md += ["## Does the best cell beat the search itself?", "",
           f"- cells at n≥{MIN_CELL}: **{len(cells)}**",
           f"- best: `{best_label}` at **{best:+.1%}** (n={len(best_rows)})",
           f"- median best-in-noise: **{st.median(null_max):+.1%}**",
           f"- 95th percentile in noise: **{null_max[int(.95*TRIALS)]:+.1%}**",
           f"- **corrected p = {beats:.3f}**", ""]
    md += (["**Clears the bar.**", ""] if beats <= 0.05 else
           ["**Does not clear.** A grid this size produces a cell this good from "
            "noise more than 5% of the time.", ""])

    # ---- the other tail: is any cell reliably BAD enough to invert? ----
    # A dependable loser is a winner backwards, but only if the loss is deeper
    # than the search manufactures AND the other side's price still clears. The
    # underdog scan failed exactly here: its worst cell was less extreme than
    # noise's median worst, so fading it was the same search one step removed.
    worst_label = min(cells, key=lambda k: _roi(cells[k]))
    worst_rows = cells[worst_label]
    worst = _roi(worst_rows)
    null_min = []
    rng2 = random.Random(97)
    for _ in range(TRIALS):
        w = [rng2.random() < r["p_adv"] for r in recs]
        null_min.append(min(_roi(v, w) for v in cells.values()))
    below = sum(1 for m in null_min if m <= worst) / TRIALS
    null_min.sort()
    md += ["## The other tail — is anything reliably bad enough to invert?", "",
           f"- worst cell: `{worst_label}` at **{worst:+.1%}** (n={len(worst_rows)})",
           f"- median worst-in-noise: **{st.median(null_min):+.1%}**",
           f"- **corrected p = {below:.3f}**",
           f"- backing the OTHER side of that cell instead: "
           f"**{_fmt(_flip(worst_rows, recs))}**", ""]
    md += (["A loss deeper than the search manufactures, so the reversal is "
            "worth carrying forward.", ""] if below <= 0.05 else
           ["**Not invertible.** The worst of these cells is no more extreme "
            "than the worst a grid this size throws up by chance, so fading it "
            "is the same search one step removed - and the reversal still has "
            "to pay the vig on the other side.", ""])

    pre = [r for r in best_rows if recs[r["_i"]]["date"] < HOLDOUT_FROM]
    post = [r for r in best_rows if recs[r["_i"]]["date"] >= HOLDOUT_FROM]
    seq = [_roi(view_adv([r for r in recs if r["margin"] >= t]))
           for t in MARGIN_STEPS]
    runs = best_run = 0
    for v in seq:
        runs = runs + 1 if v > baseline else 0
        best_run = max(best_run, runs)
    checks = [
        (f"n >= 100 (n={len(best_rows)})", len(best_rows) >= 100),
        (f"margin plateau above baseline (longest={best_run})", best_run >= 3),
        (f"corrected p <= 0.05 (p={beats:.3f})", beats <= 0.05),
        (f"holdout positive ({_roi(post):+.1%}, n={len(post)})",
         bool(post) and _roi(post) > 0),
        (f"beats the back-advantage baseline of {baseline:+.1%}", best > baseline),
    ]
    md += [f"- in-sample: {_fmt(pre)}", f"- holdout: {_fmt(post)}", "",
           "## Scored against the pre-registered bar", "",
           "| requirement | met |", "|---|---|"]
    for label, ok in checks:
        md.append(f"| {label} | {'✅' if ok else '❌'} |")
    md += ["", ("**PROMOTABLE** — all five met." if all(o for _, o in checks)
                else "**NOT promotable.** Recorded, not shipped."), ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "bvp_margin.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
