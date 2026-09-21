"""
Are the live rule's own four thresholds set correctly?

WHY THIS AND NOT A SEVENTEENTH SIGNAL
Sixteen signal hunts have found nothing, and ev_model explained why: everything
we track is already in the price. But every one of those asked "what ELSE could
select a bet". None asked whether the gates already doing the selecting are
tuned. The four constants below were set early, some on thin data, and have
never been swept:

    MIN_READINGS   2      quotes needed before the book is read at all
    MAX_SPREAD     0.15   wider than this is not a real two-sided market
    IMBALANCE_MIN  0.20   resting-size lean that counts as confirmation
    LINE_MOVE_MIN  0.01   implied-probability move that counts as a discount

Plus one structural question raised by the record: confirmation currently fires
on drift>0 OR imbalance>threshold. Requiring BOTH looked materially better in a
first pass - 2-of-2 returned +11.8% against -11.2% for 0-of-2 - but at p=0.126,
which is exactly why it needs this treatment rather than a table.

HOW THE BACKTEST WORKS
Each historical board is re-evaluated under every parameter combination, using
the same order-book log the live rule read that day. That produces a different
set of picks per combination, each graded against real results. It is the rule
itself being backtested, not a signal layered on top.

WHY THE CORRECTION STILL MATTERS
96 combinations is a grid, and this dataset manufactures winners from grids -
the 75-cell price scan produced a best cell BELOW its own noise median. So the
live configuration is the baseline, and the only question is whether any
combination beats it by more than sweeping 96 of them manufactures. Outcomes are
redrawn from de-vigged closing prices; every combination is re-scored; the best
improvement over baseline is recorded; repeat.

Writes output/rule_tuning.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from pathlib import Path

from . import consensus as C, grade, mlb_api
from .pregame_money import HOLDOUT_FROM, _implied

log = logging.getLogger("rule_tuning")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 2000

READINGS = [2, 3, 5]
SPREADS = [0.10, 0.15, 0.25]
IMBALANCES = [0.0, 0.20, 0.40, 0.60]
MOVES = [0.005, 0.01, 0.02, 0.03]
BOTH = [False, True]

LIVE = (C.MIN_READINGS, C.MAX_SPREAD, C.IMBALANCE_MIN, C.LINE_MOVE_MIN, False)


def _metrics(day: dict, min_reads: int, max_spread: float) -> dict:
    """consensus.book_metrics, parameterised. Same arithmetic, different gates."""
    out = {}
    for pk_s, g in (day.get("games") or {}).items():
        reads = [r for r in (g.get("readings") or [])
                 if not r.get("empty")
                 and isinstance(r.get("bid"), (int, float))
                 and isinstance(r.get("ask"), (int, float))
                 and r["ask"] > r["bid"] and (r["ask"] - r["bid"]) <= max_spread]
        if len(reads) < min_reads:
            continue
        reads.sort(key=lambda r: r.get("t", 0))
        f, l = reads[0], reads[-1]
        drift = (l["bid"] + l["ask"]) / 2 - (f["bid"] + f["ask"]) / 2
        bs, as_ = l.get("bid_sz") or 0, l.get("ask_sz") or 0
        imb = (bs - as_) / (bs + as_) if (bs + as_) > 0 else 0.0
        try:
            out[int(pk_s)] = {"drift": drift, "imbalance": imb}
        except (TypeError, ValueError):
            continue
    return out


def collect() -> list[dict]:
    """One row per game that could ever be a pick, with everything the gates need."""
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            books = json.loads((OUTPUT_DIR / f"pm_books_{date}.json").read_text())
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
            odds = (pc.get("advantage_moneyline") if maj == adv
                    else pc.get("opponent_moneyline"))
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            shift = (pc.get("line_check") or {}).get("implied_shift")
            if not isinstance(odds, int) or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            tot = _implied(a_ml) + _implied(o_ml)
            rows.append({
                "date": date, "pk": g.get("game_pk"), "matchup": m,
                "bet": maj, "odds": odds, "won": res["winner"] == maj,
                "is_adv": maj == adv,
                "p": (_implied(odds) / tot) if tot > 0 else 0.5,
                # signed toward the side we would back
                "toward": ((shift if maj == adv else -shift)
                           if isinstance(shift, (int, float)) else None),
                "books": books,
            })
    return rows


def picks_for(rows, params) -> list[dict]:
    min_reads, max_spread, imb_min, move_min, both = params
    cache: dict = {}
    out = []
    for r in rows:
        key = (r["date"], min_reads, max_spread)
        if key not in cache:
            cache[key] = _metrics(r["books"], min_reads, max_spread)
        m = cache[key].get(r["pk"])
        if not m:
            continue
        d_ok, i_ok = m["drift"] > 0, m["imbalance"] > imb_min
        toward_adv = (d_ok and i_ok) if both else (d_ok or i_ok)
        if not (toward_adv if r["is_adv"] else not toward_adv):
            continue
        if r["toward"] is None or r["toward"] > -move_min:
            continue                       # no price discount
        out.append(r)
    return out


def _roi(rs, wins=None) -> float:
    if not rs:
        return 0.0
    u = 0.0
    for r in rs:
        won = r["won"] if wins is None else wins[r["pk"]]
        u += grade.american_profit(r["odds"]) if won else -1
    return u / len(rs)


def build() -> str:
    rows = collect()
    md = ["# Tuning the live rule's own thresholds", "",
          "_Sixteen signal hunts found nothing, and every one asked what ELSE "
          "could select a bet. None asked whether the gates already doing the "
          "selecting are tuned. These four constants were set early, some on "
          "thin data, and have never been swept._", "",
          f"- games reaching the book gate (handle+tickets already agree): "
          f"**{len(rows)}**", ""]
    if len(rows) < 100:
        return "\n".join(md + ["Too few games.", ""])

    combos = [(a, b, c, d, e) for a in READINGS for b in SPREADS
              for c in IMBALANCES for d in MOVES for e in BOTH]
    scored = {}
    for p in combos:
        sel = picks_for(rows, p)
        if len(sel) >= 25:
            scored[p] = sel
    base = picks_for(rows, LIVE)
    base_roi = _roi(base)
    md += [f"- parameter combinations tried: **{len(combos)}** "
           f"({len(scored)} produced ≥25 picks)",
           f"- **live configuration**: readings≥{LIVE[0]}, spread≤{LIVE[1]}, "
           f"imbalance>{LIVE[2]}, move≥{LIVE[3]:.1%}, confirm=either",
           f"- live result: **{_roi(base):+.1%}** over **{len(base)}** picks", ""]
    if not scored:
        return "\n".join(md + ["No combination produced enough picks.", ""])

    ranked = sorted(scored.items(), key=lambda kv: -_roi(kv[1]))
    md += ["## Top ten configurations", "",
           "| readings | spread | imbalance | move | confirm | picks | ROI | vs live |",
           "|---|---|---|---|---|---|---|---|"]
    for p, sel in ranked[:10]:
        md.append(f"| ≥{p[0]} | ≤{p[1]} | >{p[2]} | ≥{p[3]:.1%} | "
                  f"{'BOTH' if p[4] else 'either'} | {len(sel)} | "
                  f"**{_roi(sel):+.1%}** | {_roi(sel)-base_roi:+.1f}pts |")
    md.append("")

    # ---- does the best beat the sweep itself? ----
    best_p, best_sel = ranked[0]
    best_gain = _roi(best_sel) - base_roi
    rng = random.Random(881)
    null = []
    for _ in range(TRIALS):
        wins = {r["pk"]: rng.random() < r["p"] for r in rows}
        nb = _roi(base, wins)
        null.append(max(_roi(s, wins) - nb for s in scored.values()))
    beats = sum(1 for x in null if x >= best_gain) / TRIALS
    null.sort()
    md += ["## Does the best configuration beat the sweep itself?", "",
           f"- best gain over live: **{best_gain:+.1f} points**",
           f"- median best-gain from redrawn outcomes: "
           f"**{st.median(null)*100:+.1f} points**",
           f"- 95th percentile: **{null[int(.95*TRIALS)]*100:+.1f} points**",
           f"- **corrected p = {beats:.3f}**", ""]
    md += (["**Clears.** A retune is justified.", ""] if beats <= 0.05 else
           ["**Does not clear.** Sweeping this many combinations produces a gain "
            "this large from noise more often than 5% of the time, so the "
            "current settings are not demonstrably wrong.", ""])

    pre = [r for r in best_sel if r["date"] < HOLDOUT_FROM]
    post = [r for r in best_sel if r["date"] >= HOLDOUT_FROM]
    md += [f"- best config in-sample: **{_roi(pre):+.1%}** (n={len(pre)}) · "
           f"holdout: **{_roi(post):+.1%}** (n={len(post)})",
           f"- live in-sample: **{_roi([r for r in base if r['date']<HOLDOUT_FROM]):+.1%}** · "
           f"holdout: **{_roi([r for r in base if r['date']>=HOLDOUT_FROM]):+.1%}**", ""]

    # ---- one parameter at a time, holding the rest live ----
    md += ["## One parameter at a time (others held at live values)", "",
           "_A single threshold moved in isolation is a far smaller search than "
           "the grid, and a real effect should show up as a trend rather than a "
           "spike._", "",
           "| parameter | value | picks | ROI |", "|---|---|---|---|"]
    names = ["min readings", "max spread", "imbalance min", "line move min", "confirm"]
    for i, values in enumerate([READINGS, SPREADS, IMBALANCES, MOVES, BOTH]):
        for v in values:
            p = list(LIVE)
            p[i] = v
            sel = picks_for(rows, tuple(p))
            mark = " ← live" if v == LIVE[i] else ""
            shown = ("BOTH" if v is True else "either") if i == 4 else v
            md.append(f"| {names[i]} | {shown}{mark} | {len(sel)} | "
                      f"{_roi(sel):+.1%} |")
    md.append("")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "rule_tuning.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
