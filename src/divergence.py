"""
When the model loves a team and the market does not, who is right?

THE HYPOTHESIS, IN THE USER'S WORDS
"When the heavy stat favourite is only -150 or less, that should be a tell that
the other team will win."

That is a sharper idea than anything in the by-price slices, because it is not
about the stat model's level - it is about its DISAGREEMENT with the price. A
team the model rates far ahead, which the market prices only modestly, is a game
where the two sources of information conflict. The claim is that the market wins
those, so the disagreement itself is a signal to fade.

WHY IT IS THE RIGHT SHAPE OF IDEA
It is the Benter result. His fundamental model, run on its own, lost money; it
only became profitable once the public odds were fed INTO it as an input. The
lesson is that the market's price is not a hurdle to beat but the single best
predictor available, and a model's value lies in its deviation from it - if that
deviation has any sign at all.

This dataset already hints the sign is NEGATIVE. `ev_model` scored price x
signal interaction terms by holdout log-loss and got -0.0167 with a confidence
interval EXCLUDING zero on the wrong side: when the model deviates from the
price, the deviation actively hurts. That is one of only two intervals in this
repo that exclude zero, and it points exactly where this hypothesis points.

WHAT IS MEASURED
  margin        the board's own index gap, statistical_advantage.{home,away}_score
  market        the de-vigged implied probability of the stat side
  divergence    percentile(margin) - percentile(market), so "how much more the
                model likes them than the market does", in units that do not
                depend on the index's scale

Two views, because they answer to different audiences:
  1. the explicit grid - margin quartile x the stat side's price band, including
     the exact cell named above
  2. divergence quintiles - uses every game instead of a cell, so it actually
     has power, and is the version the conclusion rests on

THE CONTROL THAT DECIDES IT
Fading a stat favourite priced at -150 means BACKING a dog; fading a stat side
that is a dog means backing a favourite. Those two have completely different
baselines, and a naive "fading works" can be nothing but the favourite-backing
baseline. So every fade cell is reported against backing the same price band
irrespective of the model, and the delta is the statistic.

Pre-registered: max-statistic permutation across the quintiles, split-half
reliability on the quintile shape, holdout split. Writes output/divergence.md.
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

log = logging.getLogger("divergence")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MIN_CELL = 30
MIN_HALF = 15
TRIALS = 3000
QUINTILES = 5


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
            sa = g.get("statistical_advantage") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            hs, as_ = sa.get("home_score"), sa.get("away_score")
            if (not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int)
                    or not isinstance(hs, (int, float))
                    or not isinstance(as_, (int, float))):
                continue
            away, home = m.split(" @ ")
            # the index gap, oriented so it is how far AHEAD the stat side is
            margin = (hs - as_) if adv == home else (as_ - hs)
            if margin <= 0:
                continue          # advantage_team disagrees with the index; skip
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue
            recs.append({
                "date": date, "adv_odds": a_ml, "opp_odds": o_ml,
                "adv_won": res["winner"] == adv, "margin": margin,
                "p_adv": _implied(a_ml) / tot,
            })
    return recs


def _pct(vals: list[float]) -> list[float]:
    """Percentile rank of each value within the list, ties shared."""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    out = [0.0] * len(vals)
    n = len(vals)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        share = ((i + j) / 2) / max(n - 1, 1)
        for k in range(i, j + 1):
            out[order[k]] = share
        i = j + 1
    return out


def _roi(rows) -> float:
    if not rows:
        return 0.0
    return sum(grade.american_profit(o) if w else -1 for o, w in rows) / len(rows)


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w = sum(1 for _, won in rows if won)
    u = sum(grade.american_profit(o) if won else -1 for o, won in rows)
    tail = "" if len(rows) >= MIN_CELL else " _(thin)_"
    return f"{w}-{len(rows)-w} · {u:+.1f}u · **{_roi(rows):+.1%}** (n={len(rows)}){tail}"


def _back_adv(recs):
    return [(r["adv_odds"], r["adv_won"]) for r in recs]


def _fade_adv(recs):
    return [(r["opp_odds"], not r["adv_won"]) for r in recs]


PRICE_BANDS = [
    ("stat side ≤-200", lambda o: o <= -200),
    ("stat side -199..-151", lambda o: -199 <= o <= -151),
    ("stat side -150..-110", lambda o: -150 <= o <= -110),
    ("stat side -109..+109", lambda o: -109 <= o <= 109),
    ("stat side ≥+110", lambda o: o >= 110),
]


def build() -> str:
    recs = collect()
    md = ["# When the model loves a team and the market doesn't, who is right?", "",
          "_The hypothesis: a team the stat model rates far ahead, which the "
          "market prices only modestly, is a game where the two disagree - and "
          "the claim is the market wins those. This is not about the stat "
          "model's level but about its DEVIATION from the price, which is the "
          "Benter framing: the price is the best predictor available, and a "
          "model is worth only what its deviation from it is worth._", "",
          f"- graded games with both an index gap and a two-sided price: "
          f"**{len(recs)}**", ""]
    if len(recs) < 200:
        return "\n".join(md + ["Not enough graded games.", ""])

    margins = [r["margin"] for r in recs]
    mp = _pct(margins)
    pp = _pct([r["p_adv"] for r in recs])
    for r, a, b in zip(recs, mp, pp):
        r["m_pct"], r["p_pct"] = a, b
        r["div"] = a - b            # model more confident than market

    # --- view 1: the explicit grid the question was asked in ---------------
    md += ["## The grid the question was asked in", "",
           "_Margin quartile is the board's own index gap. Each cell backs the "
           "stat side; the italic note is what FADING it returned instead._", "",
           "| | " + " | ".join(nm for nm, _ in PRICE_BANDS) + " |",
           "|---|" + "---|" * len(PRICE_BANDS)]
    qs = sorted(margins)
    cuts = [qs[int(q * (len(qs) - 1))] for q in (0.25, 0.5, 0.75)]
    qlabels = ["smallest gap (Q1)", "Q2", "Q3", "biggest gap (Q4)"]

    def _q(r) -> int:
        return sum(1 for c in cuts if r["margin"] > c)

    for qi, ql in enumerate(qlabels):
        cells = []
        for _, test in PRICE_BANDS:
            sub = [r for r in recs if _q(r) == qi and test(r["adv_odds"])]
            if not sub:
                cells.append("—")
                continue
            cells.append(f"back {_roi(_back_adv(sub)):+.0%} / fade "
                         f"{_roi(_fade_adv(sub)):+.0%} (n={len(sub)})")
        md.append(f"| **{ql}** | " + " | ".join(cells) + " |")
    md.append("")

    named = [r for r in recs if _q(r) == 3 and -150 <= r["adv_odds"] <= -110]
    md += ["### The exact cell named", "",
           "_biggest index gap (Q4), stat side priced -150..-110 - the model "
           "loves them, the market only mildly does_", "",
           f"- backing the stat side: {_fmt(_back_adv(named))}",
           f"- **fading it** (backing the other team): {_fmt(_fade_adv(named))}", ""]
    if len(named) < MIN_CELL:
        md += [f"_n={len(named)}. One cell of a 20-cell grid, below the n=30 "
               "floor - readable, not actionable. The quintile view below is "
               "the powered version of the same question._", ""]

    # --- view 2: divergence quintiles, which use every game ----------------
    md += ["## Divergence quintiles (the powered version)", "",
           "_`divergence` = percentile(index gap) - percentile(de-vigged price). "
           "High means the model likes them much more than the market does. Each "
           "row backs the stat side, fades the stat side, and - the control that "
           "decides it - backs the SAME price band irrespective of the model, "
           "because fading a -150 favourite just means backing a dog._", "",
           "| divergence | back stat side | fade stat side | control: same "
           "prices, any model read | fade minus control |",
           "|---|---|---|---|---|"]
    for i, r in enumerate(recs):
        r["_i"] = i
    srt = sorted(recs, key=lambda r: r["div"])
    size = len(srt) // QUINTILES
    groups = []
    for i in range(QUINTILES):
        lo = i * size
        hi = len(srt) if i == QUINTILES - 1 else (i + 1) * size
        groups.append(srt[lo:hi])
    deltas = []
    for i, grp in enumerate(groups):
        fade = _fade_adv(grp)
        # control: the same games' opponent prices, but graded as if the model
        # had no opinion - i.e. back whichever side sits in that price range
        # across ALL games, not just these
        band_lo = min(o for o, _ in fade)
        band_hi = max(o for o, _ in fade)
        ctrl = [(r["adv_odds"], r["adv_won"]) for r in recs
                if band_lo <= r["adv_odds"] <= band_hi]
        ctrl += [(r["opp_odds"], not r["adv_won"]) for r in recs
                 if band_lo <= r["opp_odds"] <= band_hi]
        d = (_roi(fade) - _roi(ctrl)) * 100
        deltas.append(d)
        md.append(f"| Q{i+1} ({grp[0]['div']:+.2f}..{grp[-1]['div']:+.2f}) | "
                  f"{_fmt(_back_adv(grp))} | {_fmt(fade)} | {_fmt(ctrl)} | "
                  f"**{d:+.1f} pts** |")
    md.append("")

    top = groups[-1]
    md += [f"_Q5 is the hypothesis: the {len(top)} games where the model is "
           "most out of step with the price._", ""]

    # --- correction for having scanned five quintiles ----------------------
    plan = []
    for grp in groups:
        plan.append([(r["_i"], grade.american_profit(r["opp_odds"])) for r in grp])
    probs = [r["p_adv"] for r in recs]
    rng = random.Random(613)
    null = []
    for _ in range(TRIALS):
        flips = [rng.random() < q for q in probs]
        best = None
        for pl in plan:
            v = sum(-1 if flips[i] else w for i, w in pl) / len(pl)
            best = v if best is None else max(best, v)
        null.append(best * 100)
    obs = _roi(_fade_adv(top)) * 100
    p = (sum(1 for x in null if x >= obs) + 1) / (len(null) + 1)
    md += ["## Does the best quintile beat the search that found it?", "",
           f"- fading the stat side in the top quintile: **{obs:+.1f}%**",
           f"- biggest a redraw manufactures across five quintiles: median "
           f"**{st.median(null):+.1f}%**, 95th pct "
           f"**{sorted(null)[int(.95*len(null))]:+.1f}%**",
           f"- **corrected p = {p:.3f}**", "",
           ("**Clears the scan.**" if p < 0.05 else
            "**Does not clear the scan** on its own."), ""]

    # --- split-half on the quintile SHAPE ----------------------------------
    rh = random.Random(88)
    halves = ([], [])
    for r in recs:
        halves[0 if rh.random() < 0.5 else 1].append(r)
    pairs = []
    md += ["## Does the shape repeat? (split-half)", "",
           "| divergence | fade ROI, half A | fade ROI, half B |", "|---|---|---|"]
    for i in range(QUINTILES):
        members = {r["_i"] for r in groups[i]}
        sub = [[r for r in h if r["_i"] in members] for h in halves]
        if min(len(x) for x in sub) < MIN_HALF:
            continue
        a, b = _roi(_fade_adv(sub[0])) * 100, _roi(_fade_adv(sub[1])) * 100
        pairs.append((a, b))
        md.append(f"| Q{i+1} | {a:+.1f}% | {b:+.1f}% |")
    md.append("")
    if len(pairs) >= 4:
        r = st.correlation([x for x, _ in pairs], [y for _, y in pairs])
        md += [f"- **split-half r = {r:+.2f}** over {len(pairs)} quintiles", "",
               ("_Positive: the divergence shape is at least partly "
                "repeatable._" if r > 0.3 else
                "_Not repeatable. The quintile pattern in one half does not "
                "predict the other, so the monotonic-looking column above is "
                "noise read as a trend._"), ""]
    else:
        md += ["_Too few quintiles survive both halves to correlate._", ""]

    pre = [r for r in top if r["date"] < HOLDOUT_FROM]
    post = [r for r in top if r["date"] >= HOLDOUT_FROM]
    md += ["## Top quintile over time", "",
           f"- in-sample: {_fmt(_fade_adv(pre))}",
           f"- holdout: {_fmt(_fade_adv(post))}", "",
           "## How to read this", "",
           "- the **fade minus control** column is the only number that "
           "isolates the disagreement; a raw fade ROI includes whatever "
           "backing that price range did all season",
           "- `ev_model` already found price x signal interactions at -0.0167 "
           "holdout log-loss with a CI excluding zero on the wrong side, which "
           "is the same claim measured with every game instead of a cell. If "
           "the delta column here is positive AND split-half holds, the two "
           "agree and there is something to build on",
           "- nothing here changes the board on its own.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "divergence.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
