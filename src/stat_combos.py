"""
Every stat in the board, crossed with line movement, price, and each other.

WHAT WAS ASKED FOR
All seven stat signals - bvp, pen, consistency, margin, form, park, record -
tested against line movement at several increments, against price bands, and in
every pairwise combination. That is the widest search in this repo by some
margin, so the correction matters more here than anywhere.

THE ARITHMETIC OF THE SEARCH
    7 stats x 4 line increments      = 28
    7 stats x 5 price bands          = 35
    21 pairs x agree/disagree        = 42
                                     ~105 cells before anything is stacked

This dataset has produced a best-looking cell from every grid tried: the 75-cell
price scan came in BELOW its own noise median, the 64-cell underdog scan landed a
tenth of a point off its, and the 113-cell team scan reached p=0.078 and still
failed. At ~105 cells the expected best-from-noise is large, and the only
question worth asking is whether anything beats THAT.

SO THREE THINGS DECIDE IT, not the table
  1. max-statistic over every cell at once
  2. split-half - do the good cells stay good? This has killed three candidates
     cleanly and endorsed one (near_miss, r=+0.88)
  3. log-loss with ALL pairwise interactions, scored out of sample. If any
     combination genuinely carries information, a model given every one of them
     will predict better. If it predicts worse, the combinations are noise and
     the model is memorising it.

Population: every game where handle and tickets already agree - the pool the
rule selects from - backing the consensus side.

Writes output/stat_combos.md.
"""

from __future__ import annotations

import glob
import itertools
import json
import logging
import math
import random
import statistics as st
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("stat_combos")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MIN_CELL = 30
TRIALS = 2000
EPS = 1e-6

STATS = ["bvp", "pen", "consistency", "margin", "form", "park", "record"]
MOVES = [0.0, 0.005, 0.01, 0.02]
BANDS = [("≤-150", lambda o: o <= -150), ("-149..-120", lambda o: -149 <= o <= -120),
         ("-119..-101", lambda o: -119 <= o <= -101),
         ("+100..+139", lambda o: 100 <= o <= 139), ("≥+140", lambda o: o >= 140)]


def collect() -> list[dict]:
    rows = []
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
            chk = g.get("public_check") or {}
            maj = (g.get("public_majority") or {}).get("team")
            adv = pc.get("advantage_team")
            m = g.get("matchup") or ""
            if chk.get("money") != "with public" or not maj or not adv or " @ " not in m:
                continue
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            odds = a_ml if maj == adv else o_ml
            if not isinstance(odds, int) or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = m.split(" @ ")

            def toward(val, team):
                if not isinstance(val, (int, float)) or not team:
                    return 0.0
                return float(val) if team == maj else -float(val)

            b, bp = g.get("bvp") or {}, g.get("bvp_pen") or {}
            form = g.get("form") or {}
            fh = (form.get("home") or {}).get("delta")
            fa = (form.get("away") or {}).get("delta")
            cons = g.get("consistency") or {}
            ch = (cons.get("home") or {}).get("back_test", {}).get("complete_win_condition")
            ca = (cons.get("away") or {}).get("back_test", {}).get("complete_win_condition")
            sit = g.get("situational") or {}

            def wp(side):
                s = sit.get(side) or {}
                w, l = s.get("wins"), s.get("losses")
                return (w / (w + l)) if isinstance(w, int) and isinstance(l, int) and (w + l) else 0.5

            margin = ((pc.get("components") or {}).get("stat_edge") or {}).get("margin")
            shift = (pc.get("line_check") or {}).get("implied_shift")
            tot = _implied(a_ml) + _implied(o_ml)
            rows.append({
                "date": date, "pk": g.get("game_pk"), "odds": odds,
                "won": res["winner"] == maj,
                "p": (_implied(odds) / tot) if tot > 0 else 0.5,
                "against": (-(shift if maj == adv else -shift)
                            if isinstance(shift, (int, float)) else 0.0),
                "x": {
                    "bvp": toward(b.get("gap"), b.get("edge_team")),
                    "pen": toward(bp.get("gap"), bp.get("edge_team")),
                    "margin": toward(margin, adv),
                    "form": ((fh - fa) if maj == home else (fa - fh))
                    if isinstance(fh, (int, float)) and isinstance(fa, (int, float)) else 0.0,
                    "consistency": float((ch - ca) if maj == home else (ca - ch))
                    if isinstance(ch, int) and isinstance(ca, int) else 0.0,
                    "park": float(g.get("park_factor") or 1.0) - 1.0,
                    "record": (wp("home") - wp("away")) if maj == home else (wp("away") - wp("home")),
                },
            })
    return rows


def _roi(rs, wins=None) -> float:
    if not rs:
        return 0.0
    u = 0.0
    for r in rs:
        won = r["won"] if wins is None else wins[r["pk"]]
        u += grade.american_profit(r["odds"]) if won else -1
    return u / len(rs)


def _fmt(rs) -> str:
    if not rs:
        return "—"
    w = sum(1 for r in rs if r["won"])
    tag = "" if len(rs) >= MIN_CELL else "_"
    return f"{tag}{_roi(rs):+.0%} ({w}-{len(rs)-w}){tag}"


def _sig(z):
    return 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))


def _fit(tr, feats, iters=3000, lr=0.15, l2=2.0):
    w = {k: 0.0 for k in feats}
    b = 0.0
    n = len(tr)
    for _ in range(iters):
        gw = {k: 0.0 for k in feats}
        gb = 0.0
        for r in tr:
            e = _sig(b + sum(w[k] * r["z"][k] for k in feats)) - (1.0 if r["won"] else 0.0)
            gb += e
            for k in feats:
                gw[k] += e * r["z"][k]
        b -= lr * gb / n
        for k in feats:
            w[k] -= lr * (gw[k] / n + l2 * w[k] / n)
    return {"w": w, "b": b, "feats": feats}


def _pred(mdl, r):
    return min(max(_sig(mdl["b"] + sum(mdl["w"][k] * r["z"][k] for k in mdl["feats"])), EPS), 1 - EPS)


def _ll(rs, ps):
    return -sum(math.log(p if r["won"] else 1 - p) for r, p in zip(rs, ps)) / len(rs)


def build() -> str:
    rows = collect()
    md = ["# Every stat, crossed with line movement, price, and each other", "",
          "_The widest search in this repo. ~105 cells, so the correction "
          "matters more here than anywhere - every grid tried has produced a "
          "best-looking cell, and the 75-cell price scan came in BELOW its own "
          "noise median._", "",
          f"- games where handle and tickets already agree: **{len(rows)}**",
          f"- backing the consensus side in all of them: **{_fmt(rows)}**", ""]
    if len(rows) < 200:
        return "\n".join(md + ["Too few games.", ""])

    meds = {k: st.median([r["x"][k] for r in rows]) for k in STATS}
    for r in rows:
        r["hi"] = {k: r["x"][k] > meds[k] for k in STATS}
    cells: dict = {}

    md += ["## Each stat x line movement against us", "",
           "| stat favours the pick | " + " | ".join(f"≥{m:.1%}" for m in MOVES) + " |",
           "|---" * (len(MOVES) + 1) + "|"]
    for k in STATS:
        row = [f"| `{k}` "]
        for mv in MOVES:
            sub = [r for r in rows if r["hi"][k] and r["against"] >= mv]
            if len(sub) >= MIN_CELL:
                cells[f"{k} + move≥{mv:.1%}"] = sub
            row.append(f"| {_fmt(sub)} ")
        md.append("".join(row) + "|")
    md.append("")

    md += ["## Each stat x price band", "",
           "| stat favours the pick | " + " | ".join(l for l, _ in BANDS) + " |",
           "|---" * (len(BANDS) + 1) + "|"]
    for k in STATS:
        row = [f"| `{k}` "]
        for lbl, t in BANDS:
            sub = [r for r in rows if r["hi"][k] and t(r["odds"])]
            if len(sub) >= MIN_CELL:
                cells[f"{k} @ {lbl}"] = sub
            row.append(f"| {_fmt(sub)} ")
        md.append("".join(row) + "|")
    md.append("")

    md += ["## Every pair of stats", "",
           "_Both favour the pick, versus the two disagreeing._", "",
           "| pair | both favour | they disagree |", "|---|---|---|"]
    for a, b in itertools.combinations(STATS, 2):
        both = [r for r in rows if r["hi"][a] and r["hi"][b]]
        dis = [r for r in rows if r["hi"][a] != r["hi"][b]]
        for lbl, sub in ((f"{a}+{b} both", both), (f"{a}+{b} split", dis)):
            if len(sub) >= MIN_CELL:
                cells[lbl] = sub
        md.append(f"| `{a}` + `{b}` | {_fmt(both)} | {_fmt(dis)} |")
    md.append("")

    best = max(cells, key=lambda k: _roi(cells[k]))
    bv = _roi(cells[best])
    rng = random.Random(1487)
    null = []
    for _ in range(TRIALS):
        wins = {r["pk"]: rng.random() < r["p"] for r in rows}
        null.append(max(_roi(v, wins) for v in cells.values()))
    pv = sum(1 for x in null if x >= bv) / TRIALS
    null.sort()
    md += ["## 1. Does the best cell beat the search?", "",
           f"- cells at n≥{MIN_CELL}: **{len(cells)}**",
           f"- best: `{best}` at **{bv:+.1%}** (n={len(cells[best])})",
           f"- median best-in-noise: **{st.median(null):+.1%}**",
           f"- 95th percentile in noise: **{null[int(.95*TRIALS)]:+.1%}**",
           f"- **corrected p = {pv:.3f}**", ""]
    md += (["**Clears.**", ""] if pv <= 0.05 else ["**Does not clear.**", ""])

    dates = sorted({r["date"] for r in rows})
    mid = dates[len(dates) // 2]
    pairs = []
    for k, v in cells.items():
        a = [r for r in v if r["date"] < mid]
        b2 = [r for r in v if r["date"] >= mid]
        if len(a) >= 12 and len(b2) >= 12:
            pairs.append((k, _roi(a), _roi(b2)))
    md += ["## 2. Split-half — do the good cells stay good?", ""]
    if len(pairs) >= 4:
        xs, ys = [p[1] for p in pairs], [p[2] for p in pairs]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        dx = sum((x - mx) ** 2 for x in xs) ** 0.5
        dy = sum((y - my) ** 2 for y in ys) ** 0.5
        r = (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (dx * dy)) if dx and dy else float("nan")
        top = sorted(pairs, key=lambda x: -x[1])[:5]
        md += ["| top-5 cell by first half | first | second |", "|---|---|---|"]
        for k, a, b2 in top:
            md.append(f"| {k} | {a:+.1%} | {b2:+.1%} |")
        md += ["", f"- correlation across **{n}** cells: **r = {r:+.2f}**", ""]
        md += (["**The ranking holds.**", ""] if r > 0.4 else
               ["**The ranking does not hold.** A cell's first-half record does "
                "not predict its second.", ""])
    else:
        md += ["Too few cells in both halves.", ""]

    # 3. the powered version: every pairwise interaction, scored out of sample
    tr = [r for r in rows if r["date"] < mid]
    ho = [r for r in rows if r["date"] >= mid]
    inter = [f"{a}*{b}" for a, b in itertools.combinations(STATS, 2)]
    stats_ = {}
    for k in STATS:
        v = [r["x"][k] for r in tr]
        m0 = sum(v) / len(v)
        sd = (sum((x - m0) ** 2 for x in v) / len(v)) ** 0.5 or 1.0
        stats_[k] = (m0, sd)
    for r in rows:
        z = {k: (r["x"][k] - stats_[k][0]) / stats_[k][1] for k in STATS}
        for a, b in itertools.combinations(STATS, 2):
            z[f"{a}*{b}"] = z[a] * z[b]
        pp = min(max(r["p"], EPS), 1 - EPS)
        z["mkt"] = math.log(pp / (1 - pp))
        r["z"] = z
    v = [r["z"]["mkt"] for r in tr]
    m0 = sum(v) / len(v)
    sd = (sum((x - m0) ** 2 for x in v) / len(v)) ** 0.5 or 1.0
    for r in rows:
        r["z"]["mkt"] = (r["z"]["mkt"] - m0) / sd

    mkt = _fit(tr, ["mkt"])
    allm = _fit(tr, ["mkt"] + STATS + inter)
    pm, pa = [_pred(mkt, r) for r in ho], [_pred(allm, r) for r in ho]
    gain = _ll(ho, pm) - _ll(ho, pa)
    d = [(-math.log(x if r["won"] else 1 - x)) - (-math.log(y if r["won"] else 1 - y))
         for r, x, y in zip(ho, pm, pa)]
    rg = random.Random(1523)
    bs = sorted(sum(q) / len(q) for q in
                ([d[rg.randrange(len(d))] for _ in d] for _ in range(4000)))
    md += ["## 3. The powered version — every pairwise combination at once", "",
           "_If any combination carries information, a model given all 21 of "
           "them predicts better. If it predicts worse, they are noise and the "
           "model memorised it._", "",
           f"- trained on **{len(tr)}** games before {mid}, scored on **{len(ho)}**",
           "", "| model | holdout log-loss |", "|---|---|",
           f"| price only | {_ll(ho, pm):.4f} |",
           f"| price + 7 stats + all 21 interactions | **{_ll(ho, pa):.4f}** |", "",
           f"- change: **{gain:+.4f}**, 95% CI **{bs[100]:+.4f} to {bs[3899]:+.4f}**", ""]
    md += (["**Combinations carry information.**", ""] if bs[100] > 0 else
           ["**No information in any combination.** Everything in the picture is "
            "already in the price, alone and together.", ""])
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "stat_combos.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
