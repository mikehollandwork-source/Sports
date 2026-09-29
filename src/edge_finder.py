"""
Edge finder: is there ANY real predictive signal in this model, and where does
price leave us closest to profitable?

After the pressure test showed every mined rule dying out-of-sample, this asks
the more fundamental questions instead of hunting for another combo:

  1. CALIBRATION - does our stat margin actually track win rate? Bucket every
     game by margin and read the win% per bucket. If it rises monotonically the
     model measures something real and the job is pricing. If it's flat, the
     model is noise and no gate can save it. This is the single most important
     table in the repo.
  2. BREAKEVEN GAP - per price bucket: the win% we NEED vs the win% we GET.
     Negative gap = structurally unprofitable there. Shows exactly which prices
     our hit rate can actually support (the underdog question, answered with math).
  3. WINNERS vs LOSERS - every continuous stat, median for wins vs losses, split
     in-sample/holdout. A stat that separates in BOTH is a lead; one that only
     separates in-sample is noise. (Many stats are compared, so treat single
     "significant" gaps with suspicion - multiple comparisons WILL manufacture some.)
  4. UNDERDOG DEEP DIVE - dogs only: price buckets, what separates winners, and
     whether any dog subset clears its breakeven bar out-of-sample.

Every candidate is reported with a HOLDOUT column. Nothing here is a rule until
it survives there. Runs on GitHub Actions. Writes output/edge_finder.md.
"""

from __future__ import annotations

import glob
import json
import statistics as st
from pathlib import Path

from . import grade, mlb_api
from .signal_backtest import signals, profile

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
HOLDOUT_FROM = "2026-07-23"


def _implied(ml: int) -> float:
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)


def collect() -> list[dict]:
    recs = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        day = json.loads(Path(f).read_text())
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for g in day.get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            sig = signals(g)
            prof = profile(g)
            if not sig or sig.get("_ml") is None:
                continue
            recs.append({"date": date, "won": res["winner"] == sig["_adv"],
                         "ml": sig["_ml"], "margin": sig.get("_margin"),
                         "prof": prof or {}, "sig": sig,
                         "holdout": date >= HOLDOUT_FROM})
    return recs


def _wl(rows: list[dict]) -> tuple[int, int, float, float]:
    n = len(rows)
    if not n:
        return 0, 0, 0.0, 0.0
    w = sum(1 for r in rows if r["won"])
    u = sum(grade.american_profit(r["ml"]) if r["won"] else -1 for r in rows)
    return w, n - w, round(u, 2), u / n


def _cell(rows: list[dict]) -> str:
    if not rows:
        return "—"
    w, l, u, roi = _wl(rows)
    return f"{w}-{l} ({w/(w+l):.0%}) · {roi:+.1%} (n={len(rows)})"


def build() -> str:
    recs = collect()
    if not recs:
        return "# Edge finder\n\n_No graded games._"
    ins = [r for r in recs if not r["holdout"]]
    hold = [r for r in recs if r["holdout"]]
    md = [f"# Edge finder — {len(recs)} games ({len(ins)} in-sample, {len(hold)} holdout)", "",
          "_Bets our stat side at its frozen price. The HOLDOUT column is the only "
          "out-of-sample evidence._", ""]

    # 1. CALIBRATION - the make-or-break question.
    md += ["## 1. Calibration — does our margin track win rate?", "",
           "_If win% climbs with margin, the model measures something real (and the "
           "problem is pricing). If it's flat, the model is noise._", "",
           "| margin bucket | ALL | in-sample | HOLDOUT |", "|---|---|---|---|"]
    buckets = [(-99, 0, "< 0 (no edge)"), (0, 0.2, "0.0–0.2"), (0.2, 0.4, "0.2–0.4"),
               (0.4, 0.6, "0.4–0.6"), (0.6, 0.9, "0.6–0.9"), (0.9, 99, "0.9+")]
    for lo, hi, lab in buckets:
        f = lambda rs, lo=lo, hi=hi: [r for r in rs if r["margin"] is not None
                                      and lo <= r["margin"] < hi]
        md.append(f"| {lab} | {_cell(f(recs))} | {_cell(f(ins))} | {_cell(f(hold))} |")
    md.append("")
    mg = [r for r in recs if r["margin"] is not None]
    if len(mg) > 30:
        hi_m = [r for r in mg if r["margin"] >= 0.5]
        lo_m = [r for r in mg if r["margin"] < 0.5]
        hw = sum(1 for r in hi_m if r["won"]) / len(hi_m) if hi_m else 0
        lw = sum(1 for r in lo_m if r["won"]) / len(lo_m) if lo_m else 0
        md += [f"_High margin (≥0.5) wins {hw:.1%} vs low margin {lw:.1%} — "
               f"a **{(hw-lw)*100:+.1f} point** spread. That spread IS the model's "
               "entire predictive claim._", ""]

    # 2. BREAKEVEN GAP - where can our hit rate actually pay?
    md += ["## 2. Breakeven gap by price — what we NEED vs what we GET", "",
           "_need% = the win rate that price requires just to break even. "
           "gap = actual − need. Positive gap = profitable territory._", "",
           "| price bucket | need% | actual (ALL) | gap | HOLDOUT actual |",
           "|---|---|---|---|---|"]
    pbuckets = [(-10000, -200, "≤ −200 (heavy chalk)"), (-200, -160, "−200 to −160"),
                (-160, -130, "−160 to −130"), (-130, -110, "−130 to −110"),
                (-110, 100, "−110 to +100 (pick'em)"), (100, 150, "+100 to +150"),
                (150, 10000, "+150 or better")]
    for lo, hi, lab in pbuckets:
        sub = [r for r in recs if lo <= r["ml"] < hi]
        hsub = [r for r in hold if lo <= r["ml"] < hi]
        if not sub:
            continue
        need = st.mean(_implied(r["ml"]) for r in sub)
        act = sum(1 for r in sub if r["won"]) / len(sub)
        md.append(f"| {lab} | {need:.1%} | {act:.1%} (n={len(sub)}) | "
                  f"**{(act-need)*100:+.1f}pts** | {_cell(hsub)} |")
    md.append("")

    # 3. WINNERS vs LOSERS on every continuous stat.
    KEYS = [("margin", "edge margin"), ("team_score_gap", "team-score gap"),
            ("offense_index_gap", "offense-index gap"), ("pitching_index_gap", "pitching-index gap"),
            ("fip_gap", "FIP gap (opp−ours)"), ("woba_neutral_gap", "wOBA gap"),
            ("iso_neutral_gap", "ISO gap"), ("k_pct_gap", "K% gap"),
            ("bvp_gap", "BvP gap"), ("form_gap", "form gap"), ("dog_price", "price (ml)")]
    md += ["## 3. What winners have in common (vs losers)", "",
           "_Median of each stat for wins vs losses. A stat that separates in BOTH "
           "columns is a lead; in-sample-only separation is noise. NOTE: 11 stats × "
           "2 windows are compared here — a couple of spurious gaps are expected._", "",
           "| stat | in-sample W / L | holdout W / L |", "|---|---|---|"]
    for k, lab in KEYS:
        def med(rows, key=k):
            v = [r["prof"].get(key) if key != "margin" else r["margin"] for r in rows]
            v = [x for x in v if isinstance(x, (int, float))]
            return st.median(v) if v else None
        iw, il = med([r for r in ins if r["won"]]), med([r for r in ins if not r["won"]])
        hw, hl = med([r for r in hold if r["won"]]), med([r for r in hold if not r["won"]])
        def fmt(a, b):
            if a is None or b is None:
                return "—"
            return f"{a:+.3f} / {b:+.3f}"
        md.append(f"| {lab} | {fmt(iw, il)} | {fmt(hw, hl)} |")
    md.append("")

    # 4. UNDERDOG DEEP DIVE - the "more dog money" question, answered with math.
    dogs = [r for r in recs if r["ml"] > 0]
    dogs_h = [r for r in dogs if r["holdout"]]
    md += [f"## 4. Underdogs — can we actually make dog money? (n={len(dogs)})", "",
           "| dog slice | ALL | in-sample | HOLDOUT |", "|---|---|---|---|"]
    def dsub(pred):
        return ([r for r in dogs if pred(r)],
                [r for r in dogs if pred(r) and not r["holdout"]],
                [r for r in dogs if pred(r) and r["holdout"]])
    rows = [("all underdogs", lambda r: True),
            ("+ margin ≥ 0.4", lambda r: (r["margin"] or -9) >= 0.4),
            ("+ margin ≥ 0.5", lambda r: (r["margin"] or -9) >= 0.5),
            ("+ consistency", lambda r: r["sig"].get("consistency") is True),
            ("+ FIP gap ≥ 0.15", lambda r: (r["prof"].get("fip_gap") or -9) >= 0.15),
            ("+ pitching-index gap > 0", lambda r: (r["prof"].get("pitching_index_gap") or -9) > 0),
            ("small dogs (+100 to +140)", lambda r: 100 <= r["ml"] <= 140),
            ("big dogs (> +140)", lambda r: r["ml"] > 140)]
    for lab, pred in rows:
        a, i, h = dsub(pred)
        md.append(f"| {lab} | {_cell(a)} | {_cell(i)} | {_cell(h)} |")
    md.append("")
    if dogs:
        need = st.mean(_implied(r["ml"]) for r in dogs)
        act = sum(1 for r in dogs if r["won"]) / len(dogs)
        md += [f"_Dogs need **{need:.1%}** to break even; we hit **{act:.1%}** "
               f"(**{(act-need)*100:+.1f} pts**). Every extra dog we add only helps "
               "if it clears that bar._", ""]

    md.append("_Multiple comparisons caveat: this file scans many slices. Treat any "
              "single green cell as a hypothesis, never a rule, until it holds in the "
              "holdout AND has a reason to be true._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "edge_finder.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
