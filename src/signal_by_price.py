"""
Every signal, sliced by the closing price of the side it names.

THE QUESTION
A signal can be flat on average and still live in one price range - "our read is
worth something only on cheap dogs", say. That is an interaction between signal
and price, and none of the previous tests looked for it directly.

WHY THIS IS THE MOST DANGEROUS TEST IN THE REPO
Price is continuous, so it can be cut a hundred ways, and each cut multiplies
the search. Seven signals x seven price buckets x two directions is ~98 chances
to find something, and this dataset has already been shown to manufacture a
+18.7% cell against a noise median of +18.6%. The grid will produce a winner.
The only question worth asking is whether it produces a BIGGER winner than the
grid alone would.

So the headline is not the best cell. It is the max-statistic permutation:
outcomes redrawn from de-vigged closing prices, every cell recomputed, the best
recorded, 3000 times. A cell only counts if it beats what the search itself
manufactures at this width.

DIRECTION IS NOT FREE
Every signal is reported both backing and fading its named side. Choosing the
direction after seeing the numbers is how a coin flip becomes a finding, so both
enter the grid and both are paid for in the correction.

THE COMPANION TEST
`ev_model` carries the properly-powered version: signal x price INTERACTION
terms scored by holdout log-loss, which uses every game rather than a cell of
them. If an interaction is real it shows up there with a tight interval. This
file is the descriptive picture; that one is the evidence.

Writes output/signal_by_price.md.
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

log = logging.getLogger("signal_by_price")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MIN_CELL = 30
TRIALS = 3000

BUCKETS = [
    ("heavy fav ≤-200", lambda o: o <= -200),
    ("fav -199..-140", lambda o: -199 <= o <= -140),
    ("fav -139..-110", lambda o: -139 <= o <= -110),
    ("pick'em -109..+109", lambda o: -109 <= o <= 109),
    ("dog +110..+139", lambda o: 110 <= o <= 139),
    ("dog +140..+199", lambda o: 140 <= o <= 199),
    ("big dog ≥+200", lambda o: o >= 200),
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
            m = g.get("matchup") or ""
            if " @ " not in m:
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = m.split(" @ ")
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            b, bp = g.get("bvp") or {}, g.get("bvp_pen") or {}
            form = g.get("form") or {}
            fh = (form.get("home") or {}).get("delta")
            fa = (form.get("away") or {}).get("delta")
            shift = (pc.get("line_check") or {}).get("implied_shift")
            lean = ((pc.get("components") or {}).get("public_fade") or {}).get("blended_lean")

            # each signal names a side, or None when it has no read
            sides = {
                "margin (advantage_team)": adv,
                "starter BvP": b.get("edge_team"),
                "bullpen BvP": bp.get("edge_team"),
                "hotter bats": (home if fh > fa else away)
                if isinstance(fh, (int, float)) and isinstance(fa, (int, float))
                and fh != fa else None,
                "line moved TOWARD": (adv if shift > 0 else opp)
                if isinstance(shift, (int, float)) and shift else None,
                "line moved AGAINST": (opp if shift > 0 else adv)
                if isinstance(shift, (int, float)) and shift else None,
                "public lean": (adv if lean > 0 else opp)
                if isinstance(lean, (int, float)) and lean else None,
            }
            tot = _implied(a_ml) + _implied(o_ml)
            recs.append({
                "date": date, "adv": adv, "opp": opp, "price": price,
                "winner": res["winner"],
                "p_adv": (_implied(a_ml) / tot) if tot > 0 else 0.5,
                "sides": sides,
            })
    return recs


def _view(recs, signal: str, fade: bool) -> list[dict]:
    """Back (or fade) the side this signal names, at that side's real price."""
    out = []
    for r in recs:
        s = r["sides"].get(signal)
        if not s:
            continue
        bet = (r["opp"] if s == r["adv"] else r["adv"]) if fade else s
        out.append({"_i": r["_i"], "odds": r["price"][bet],
                    "won": r["winner"] == bet, "invert": bet != r["adv"]})
    return out


def _stat(rows, wins=None):
    w = u = 0
    for x in rows:
        won = x["won"] if wins is None else (
            (not wins[x["_i"]]) if x["invert"] else wins[x["_i"]])
        w += 1 if won else 0
        u += grade.american_profit(x["odds"]) if won else -1
    return w, len(rows) - w, u, (u / len(rows) if rows else 0.0)


def _roi(rows, wins=None) -> float:
    return _stat(rows, wins)[3]


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w, l, u, roi = _stat(rows)
    if len(rows) < MIN_CELL:
        return f"_{roi:+.0%} (n={len(rows)})_"
    return f"**{roi:+.1%}** ({len(rows)})"


def build() -> str:
    recs = collect()
    for i, r in enumerate(recs):
        r["_i"] = i
    md = ["# Every signal, sliced by closing price", "",
          "_A signal can be flat overall and still live in one price range. "
          "Price is also the easiest thing in this dataset to over-slice, so the "
          "grid below is scored against what a grid this wide manufactures from "
          "noise._", "", f"- graded games: **{len(recs)}**", "",
          "_Cells show ROI and (n). Italic cells are below "
          f"n={MIN_CELL} and are excluded from the correction._", ""]
    if len(recs) < 200:
        return "\n".join(md + ["Too few games.", ""])

    signals = list(recs[0]["sides"].keys())
    cells: dict = {}
    for fade in (False, True):
        md += [f"## {'FADING' if fade else 'BACKING'} the side each signal names",
               "", "| signal | overall | " + " | ".join(l for l, _ in BUCKETS) + " |",
               "|---" * (len(BUCKETS) + 2) + "|"]
        for sig in signals:
            base = _view(recs, sig, fade)
            row = [f"| {sig} | {_fmt(base)} "]
            for lbl, test in BUCKETS:
                sub = [x for x in base if test(x["odds"])]
                if len(sub) >= MIN_CELL:
                    cells[f"{'fade' if fade else 'back'} {sig} @ {lbl}"] = sub
                row.append(f"| {_fmt(sub)} ")
            md.append("".join(row) + "|")
        md.append("")

    if not cells:
        return "\n".join(md + [f"No cell reaches n={MIN_CELL}.", ""])

    best_label = max(cells, key=lambda k: _roi(cells[k]))
    best_rows = cells[best_label]
    best = _roi(best_rows)
    rng = random.Random(307)
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
           [f"**Does not clear.** A grid of {len(cells)} cells produces one this "
            "good from noise more than 5% of the time, so the number is the "
            "width of the search, not a property of the price.", ""])

    pre = [r for r in best_rows if recs[r["_i"]]["date"] < HOLDOUT_FROM]
    post = [r for r in best_rows if recs[r["_i"]]["date"] >= HOLDOUT_FROM]
    w, l, u, _ = _stat(pre)
    w2, l2, u2, _ = _stat(post)
    md += [f"- in-sample: {w}-{l} · {_roi(pre):+.1%} (n={len(pre)})",
           f"- holdout: {w2}-{l2} · {_roi(post):+.1%} (n={len(post)})", "",
           "_The properly-powered version of this question lives in "
           "`ev_model.md`: signal x price interaction terms scored by holdout "
           "log-loss, which uses every game instead of a cell of them._"]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "signal_by_price.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
