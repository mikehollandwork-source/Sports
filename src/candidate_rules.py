"""
Candidate rules: take the two patterns the edge finder actually surfaced and
test them as REAL gates, holdout included, before any of them touch the board.

What the edge finder found (413 games):
  * margin is the model's only genuine signal, and only at the top: margin >= 0.5
    wins 61.9% vs 50.0% below it. The 0.2-0.4 margin band is a dead zone
    (45% win, -19.1% ROI over n=127) - and the consistency core path is what lets
    that band onto the board.
  * price is structural: big dogs (> +140) hit 16.7% against a 36.2% breakeven
    bar (-19.5 pts). Heavy chalk needs ~70% and gets ~68%. The only bucket with a
    positive gap is -130..-110 (+1.2 pts), with +100..+150 essentially flat.

So the candidates all combine a margin requirement with a price window. Each is
reported with bets/day so we can see what it does to volume, and every one is
judged on the HOLDOUT column. Writes output/candidate_rules.md.
"""

from __future__ import annotations

from . import grade
from .pressure_test import collect, HOLDOUT_FROM

OUTPUT_DIR = __import__("pathlib").Path(__file__).resolve().parent.parent / "output"


def _roi(rows):
    if not rows:
        return None
    w = sum(1 for r in rows if r["won"])
    u = sum(grade.american_profit(r["ml"]) if r["won"] else -1 for r in rows)
    return w, len(rows) - w, round(u, 2), u / len(rows)


def _cell(rows):
    r = _roi(rows)
    if not r:
        return "—"
    w, l, u, roi = r
    return f"{w}-{l} ({w/(w+l):.0%}) · {u:+.1f}u · **{roi:+.1%}** (n={w+l})"


def build() -> str:
    recs = [r for r in collect() if r["ml"] is not None]
    if not recs:
        return "# Candidate rules\n\n_No graded games._"
    days = len({r["date"] for r in recs})
    hdays = len({r["date"] for r in recs if r["date"] >= HOLDOUT_FROM})

    margin = lambda r: r["sig"].get("_margin")
    core = lambda r: (r["sig"].get("margin") is True or r["sig"].get("consistency") is True)
    fade_ok = lambda r: (not r["is_tail"]) if r["has_book"] else True
    live = lambda r: (core(r) and fade_ok(r) and not r["mild_public"])

    def mg(r, thr):
        m = margin(r)
        return m is not None and m >= thr

    def price_in(r, lo, hi):
        return isinstance(r["ml"], int) and lo <= r["ml"] <= hi

    CANDS = [
        ("current live gate (baseline)", live),
        ("A. margin ≥0.5 only (drop consistency path)", lambda r: mg(r, 0.5)),
        ("B. margin ≥0.5 + fade gate", lambda r: mg(r, 0.5) and fade_ok(r)),
        ("C. margin ≥0.5 + no big dogs (ml ≤ +140)",
         lambda r: mg(r, 0.5) and price_in(r, -10000, 140)),
        ("D. margin ≥0.5 + price window −180..+140",
         lambda r: mg(r, 0.5) and price_in(r, -180, 140)),
        ("E. margin ≥0.5 + fade + price −180..+140",
         lambda r: mg(r, 0.5) and fade_ok(r) and price_in(r, -180, 140)),
        ("F. live gate + no big dogs", lambda r: live(r) and price_in(r, -10000, 140)),
        ("G. live gate + margin required (no consistency-only)",
         lambda r: live(r) and mg(r, 0.5)),
        ("H. price window only, no stat gate (−160..+140)",
         lambda r: price_in(r, -160, 140)),
        ("I. margin ≥0.4 + price −180..+140",
         lambda r: mg(r, 0.4) and price_in(r, -180, 140)),
    ]

    md = [f"# Candidate rules — {len(recs)} games over {days} days "
          f"({hdays} holdout days)", "",
          "_Every rule bets our stat side at the frozen price. The HOLDOUT column "
          "decides; in-sample is shown only to expose curve-fitting (a rule that "
          "looks great in-sample and dies in holdout is noise)._", "",
          "| candidate | ALL | in-sample | HOLDOUT | bets/day |",
          "|---|---|---|---|---|"]
    for label, pred in CANDS:
        sub = [r for r in recs if pred(r)]
        ins = [r for r in sub if r["date"] < HOLDOUT_FROM]
        hold = [r for r in sub if r["date"] >= HOLDOUT_FROM]
        md.append(f"| {label} | {_cell(sub)} | {_cell(ins)} | {_cell(hold)} | "
                  f"{len(sub)/days:.1f} |")
    md.append("")

    # margin threshold sweep crossed with a sane price window - is there a stable
    # plateau (good) or a single lucky spike (overfit)?
    md += ["## Margin threshold sweep (inside price window −180..+140)", "",
           "_A real edge shows a PLATEAU across neighbouring thresholds. A single "
           "spiking cell with dips either side is noise._", "",
           "| margin ≥ | ALL | in-sample | HOLDOUT | bets/day |", "|---|---|---|---|---|"]
    for thr in (0.3, 0.4, 0.5, 0.6, 0.7):
        sub = [r for r in recs if mg(r, thr) and price_in(r, -180, 140)]
        ins = [r for r in sub if r["date"] < HOLDOUT_FROM]
        hold = [r for r in sub if r["date"] >= HOLDOUT_FROM]
        md.append(f"| {thr:.1f} | {_cell(sub)} | {_cell(ins)} | {_cell(hold)} | "
                  f"{len(sub)/days:.1f} |")
    md.append("")

    # the dead zone, stated plainly
    dz = [r for r in recs if (margin(r) or -9) >= 0.2 and (margin(r) or 9) < 0.4]
    md += ["## The margin dead zone (0.2–0.4) — what the consistency path lets in", "",
           f"- as played: {_cell(dz)}", ""]

    md.append("_Multiple comparisons: 10 candidates × 3 windows are scanned here. "
              "Prefer a rule with a PLATEAU and a reason over the single best cell._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "candidate_rules.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
