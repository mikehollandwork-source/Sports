"""
Every possible combination of the seven stat signals - all 127 subsets.

WHAT IS ENUMERATED
Seven signals give 2^7 - 1 = 127 non-empty subsets. For each, the cell is the
games where EVERY stat in that subset favours the side the rule is backing.
Singles, pairs, triples, all the way up to all seven at once. Nothing is left
out, which is what was asked.

THE PROBLEM WITH ASKING FOR EVERY COMBINATION
It is the widest search possible on this data, so the best cell is guaranteed to
look good. That is not a risk, it is arithmetic: with 127 cells the expected
best-from-noise is high, and this repo has already watched a 75-cell scan
produce a best cell BELOW its own noise median and a 113-cell team scan reach
p=0.078 and still fail.

Worse, the subsets nest. "bvp+pen" and "bvp+pen+form" overlap heavily, so they
are not 127 independent looks - they are one look sliced 127 ways, which makes
the greenest cell even less meaningful than the count suggests.

SO THREE THINGS DECIDE IT
  1. max-statistic over all 127 at once
  2. split-half: do the good subsets stay good? This has killed three
     candidates and endorsed one, and it is the test that answers the real
     question - would acting on the best subset have worked?
  3. the size curve: if stacking stats genuinely helps, ROI should RISE with
     subset size. If it only rises as n falls, that is thinning, not signal.

Population: every game where handle and tickets already agree, backing the
consensus side.

Writes output/stat_subsets.md.
"""

from __future__ import annotations

import itertools
import logging
import random
import statistics as st
from pathlib import Path

from . import grade
from .stat_combos import STATS, collect

log = logging.getLogger("stat_subsets")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MIN_CELL = 25
TRIALS = 2000


def _roi(rs, wins=None) -> float:
    if not rs:
        return 0.0
    u = 0.0
    for r in rs:
        won = r["won"] if wins is None else wins[r["pk"]]
        u += grade.american_profit(r["odds"]) if won else -1
    return u / len(rs)


def _rec(rs):
    w = sum(1 for r in rs if r["won"])
    return f"{w}-{len(rs)-w}"


def build() -> str:
    rows = collect()
    md = ["# Every combination of the seven stats — all 127 subsets", "",
          "_Singles, pairs, triples, up to all seven at once. A cell is the "
          "games where EVERY stat in the subset favours the side we back._", "",
          f"- games where handle and tickets already agree: **{len(rows)}**",
          f"- backing the consensus side in all of them: "
          f"**{_rec(rows)} · {_roi(rows):+.1%}**", ""]
    if len(rows) < 200:
        return "\n".join(md + ["Too few games.", ""])

    meds = {k: st.median([r["x"][k] for r in rows]) for k in STATS}
    for r in rows:
        r["hi"] = {k: r["x"][k] > meds[k] for k in STATS}

    cells: dict = {}
    by_size: dict = {}
    for k in range(1, len(STATS) + 1):
        for combo in itertools.combinations(STATS, k):
            sub = [r for r in rows if all(r["hi"][c] for c in combo)]
            if len(sub) >= MIN_CELL:
                cells["+".join(combo)] = sub
                by_size.setdefault(k, []).append(("+".join(combo), sub))
    md += [f"- subsets enumerated: **127** · reaching n≥{MIN_CELL}: "
           f"**{len(cells)}**", ""]
    if not cells:
        return "\n".join(md + ["No subset reaches the minimum sample.", ""])

    md += ["## Best subset at each size", "",
           "| stats stacked | best subset | record | n | ROI |",
           "|---|---|---|---|---|"]
    for k in sorted(by_size):
        name, sub = max(by_size[k], key=lambda kv: _roi(kv[1]))
        md.append(f"| {k} | `{name}` | {_rec(sub)} | {len(sub)} | "
                  f"**{_roi(sub):+.1%}** |")
    md.append("")

    ranked = sorted(cells.items(), key=lambda kv: -_roi(kv[1]))
    md += ["## Top fifteen of all 127", "",
           "| subset | record | n | ROI |", "|---|---|---|---|"]
    for name, sub in ranked[:15]:
        md.append(f"| `{name}` | {_rec(sub)} | {len(sub)} | **{_roi(sub):+.1%}** |")
    md.append("")

    # 1. correction
    best, bsub = ranked[0]
    bv = _roi(bsub)
    rng = random.Random(1601)
    null = []
    for _ in range(TRIALS):
        wins = {r["pk"]: rng.random() < r["p"] for r in rows}
        null.append(max(_roi(v, wins) for v in cells.values()))
    pv = sum(1 for x in null if x >= bv) / TRIALS
    null.sort()
    md += ["## 1. Does the best of 127 beat the search?", "",
           f"- best: `{best}` at **{bv:+.1%}** ({_rec(bsub)}, n={len(bsub)})",
           f"- median best-in-noise: **{st.median(null):+.1%}**",
           f"- 95th percentile in noise: **{null[int(.95*TRIALS)]:+.1%}**",
           f"- **corrected p = {pv:.3f}**", ""]
    md += (["**Clears.**", ""] if pv <= 0.05 else
           ["**Does not clear.** With 127 nested subsets this is what the search "
            "itself produces.", ""])

    # 2. split-half
    dates = sorted({r["date"] for r in rows})
    mid = dates[len(dates) // 2]
    pairs = []
    for k, v in cells.items():
        a = [r for r in v if r["date"] < mid]
        b = [r for r in v if r["date"] >= mid]
        if len(a) >= 10 and len(b) >= 10:
            pairs.append((k, _roi(a), _roi(b)))
    md += ["## 2. Split-half — would acting on the best subset have worked?", ""]
    if len(pairs) >= 5:
        xs, ys = [p[1] for p in pairs], [p[2] for p in pairs]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        dx = sum((x - mx) ** 2 for x in xs) ** 0.5
        dy = sum((y - my) ** 2 for y in ys) ** 0.5
        r = (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (dx * dy)) if dx and dy else float("nan")
        top = sorted(pairs, key=lambda x: -x[1])[:5]
        md += ["| best-in-first-half subset | first | second |", "|---|---|---|"]
        for k, a, b in top:
            md.append(f"| `{k}` | {a:+.1%} | {b:+.1%} |")
        # what you'd have earned following the first half's leader
        lead = top[0][0]
        after = [r for r in cells[lead] if r["date"] >= mid]
        md += ["", f"- correlation across **{n}** subsets: **r = {r:+.2f}**",
               f"- backing `{lead}` (the first half's best) in the second half: "
               f"**{_rec(after)} · {_roi(after):+.1%}** (n={len(after)})",
               f"- backing everything in the second half: "
               f"**{_rec([r for r in rows if r['date'] >= mid])} · "
               f"{_roi([r for r in rows if r['date'] >= mid]):+.1%}**", ""]
        md += (["**The ranking holds.**", ""] if r > 0.4 else
               ["**The ranking does not hold.** Picking the best subset from one "
                "half does not beat taking everything in the next.", ""])
    else:
        md += ["Too few subsets in both halves.", ""]

    # 3. the size curve
    md += ["## 3. Does stacking more stats actually help?", "",
           "_If combining genuinely adds, ROI should rise with subset size. If "
           "it only rises as n falls, that is thinning, not signal._", "",
           "| stats stacked | subsets | median ROI | median n |", "|---|---|---|---|"]
    for k in sorted(by_size):
        rois = [_roi(v) for _n, v in by_size[k]]
        ns = [len(v) for _n, v in by_size[k]]
        md.append(f"| {k} | {len(by_size[k])} | {st.median(rois):+.1%} | "
                  f"{int(st.median(ns))} |")
    md.append("")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "stat_subsets.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
