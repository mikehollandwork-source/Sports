"""
Is the stat model worth anything when it names a FAVOURITE, or a DOG?

THE QUESTION
Everything the board measures about a team - margin, BvP, bullpen, form, park,
consistency, record - is collapsed into one output: `advantage_team`. Sliced
every way so far it is flat to negative (-3.5% over 851 games). But "flat on
average" hides a shape: a read can be worthless on chalk and worth something on
a dog, because a dog's price has more room to be wrong.

`signal_by_price` already showed the descriptive picture, and the stat side as a
moderate dog (+110..+139) is the best cell in that 75-cell grid: +16.9% over 90
games, with +14.9% in-sample and +18.3% in the holdout. Corrected p = 0.581, so
it does not clear the width of that search. That is where the question was left.

WHAT THIS ADDS - THE CONTROL THAT WAS MISSING
A price band is not a neutral container. If every team priced +110..+139 went
+15% this season, then "stat dog" returns +16.9% for having been a dog, and the
stat model contributed nothing. The previous test never checked that, so it
could not tell an edge from a price-band effect.

So every band here is reported three ways:

    stat side in the band          what we would bet
    NON-stat side in the band      same prices, opposite stat read
    delta                          what the stat model is actually worth

The delta is the statistic. It is immune to "dogs were profitable this year",
because both columns are dogs.

THE TESTS, PRE-REGISTERED
  1. max-statistic permutation over the bands - winners redrawn from de-vigged
     prices, all bands recomputed, biggest delta recorded, 3000 times. Scanning
     seven bands and reporting the best needs paying for.
  2. split-half reliability on the per-band deltas. This is the test that has
     actually discriminated in this repo: it killed the team scan (r=-0.12),
     the fade profile (r=-0.64) and the stat combos (r=-0.20), and endorsed
     near_miss (r=+0.88). A shape that does not repeat across halves is not a
     shape.
  3. in-sample vs holdout, and the interaction with line movement - the one
     signal that has held up - to see whether the two compound or overlap.

Writes output/stat_price.md.
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

log = logging.getLogger("stat_price")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MIN_CELL = 30          # below this a band is reported but kept out of the correction
MIN_HALF = 15          # below this a band is left out of the split-half
TRIALS = 3000
LINE_MIN = 0.01        # the live board's line-movement threshold

BANDS = [
    ("heavy fav ≤-200", lambda o: o <= -200),
    ("fav -199..-140", lambda o: -199 <= o <= -140),
    ("fav -139..-110", lambda o: -139 <= o <= -110),
    ("pick'em -109..+109", lambda o: -109 <= o <= 109),
    ("dog +110..+139", lambda o: 110 <= o <= 139),
    ("dog +140..+199", lambda o: 140 <= o <= 199),
    ("big dog ≥+200", lambda o: o >= 200),
]


def collect() -> list[dict]:
    """One row per graded game: both sides' prices, which was the stat side,
    who won, the de-vigged probability, and how the line moved."""
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
            tot = _implied(a_ml) + _implied(o_ml)
            shift = (pc.get("line_check") or {}).get("implied_shift")
            recs.append({
                "date": date, "adv_odds": a_ml, "opp_odds": o_ml,
                "adv_won": res["winner"] == adv,
                "p_adv": (_implied(a_ml) / tot) if tot > 0 else 0.5,
                # signed toward the stat side: negative = line moved away from it
                "toward_adv": shift if isinstance(shift, (int, float)) else None,
            })
    return recs


# --- the two views of a band -------------------------------------------------
# A band is defined on a PRICE, and each game offers two prices. The stat view
# takes the game when the stat side's price is in the band; the control takes it
# when the OPPONENT's price is in the band. Same prices, opposite stat read, and
# disjoint - a game can appear in both only if both sides land in the same band,
# which only the pick'em band allows.

def _stat_side(recs, test) -> list[dict]:
    return [{"odds": r["adv_odds"], "won": r["adv_won"], "p": r["p_adv"],
             "adv": True, "date": r["date"], "toward": r["toward_adv"]}
            for r in recs if test(r["adv_odds"])]


def _other_side(recs, test) -> list[dict]:
    return [{"odds": r["opp_odds"], "won": not r["adv_won"], "p": 1 - r["p_adv"],
             "adv": False, "date": r["date"],
             "toward": (-r["toward_adv"] if r["toward_adv"] is not None else None)}
            for r in recs if test(r["opp_odds"])]


def _roi(rows) -> float:
    if not rows:
        return 0.0
    return sum(grade.american_profit(x["odds"]) if x["won"] else -1
               for x in rows) / len(rows)


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w = sum(1 for x in rows if x["won"])
    u = sum(grade.american_profit(x["odds"]) if x["won"] else -1 for x in rows)
    tail = "" if len(rows) >= MIN_CELL else " _(thin)_"
    return (f"{w}-{len(rows)-w} · {u:+.1f}u · **{_roi(rows):+.1%}** "
            f"(n={len(rows)}){tail}")


def _redraw_roi(rows, rng) -> float:
    """ROI if every game's winner were redrawn from its de-vigged price."""
    if not rows:
        return 0.0
    return sum(grade.american_profit(x["odds"]) if rng.random() < x["p"] else -1
               for x in rows) / len(rows)


def build() -> str:
    recs = collect()
    md = ["# The stat model as a favourite and as a dog", "",
          "_Everything the board measures - margin, BvP, bullpen, form, park, "
          "consistency, record - collapses into one output: `advantage_team`. "
          "Flat overall at -3.5% over 851 games. The question here is whether "
          "it is flat everywhere, or worthless on chalk and worth something on "
          "a dog._", "",
          f"- graded games: **{len(recs)}**", ""]
    if len(recs) < 200:
        return "\n".join(md + ["Not enough graded games.", ""])

    md += ["## The control that was missing", "",
           "_A price band is not a neutral container. If every team priced "
           "+110..+139 was profitable this season, then \"stat dog\" earns its "
           "return for being a dog and the stat model contributed nothing. So "
           "each band is shown with the NON-stat side at the same prices. The "
           "**delta** is what the stat model is worth._", "",
           "| band | stat side (what we'd bet) | non-stat side (same prices) "
           "| delta |", "|---|---|---|---|"]
    rows_by_band: dict = {}
    for name, test in BANDS:
        s, o = _stat_side(recs, test), _other_side(recs, test)
        rows_by_band[name] = (s, o)
        d = (_roi(s) - _roi(o)) * 100 if s and o else None
        md.append(f"| {name} | {_fmt(s)} | {_fmt(o)} | "
                  + (f"**{d:+.1f} pts**" if d is not None else "—") + " |")
    md.append("")

    # --- the headline, corrected for having scanned seven bands -------------
    live = [(nm, s, o) for nm, (s, o) in rows_by_band.items()
            if len(s) >= MIN_CELL and len(o) >= MIN_CELL]
    if not live:
        return "\n".join(md + ["No band has enough games on both sides.", ""])
    best_nm, best_s, best_o = max(live, key=lambda t: _roi(t[1]) - _roi(t[2]))
    best_d = (_roi(best_s) - _roi(best_o)) * 100

    # band membership and payouts are fixed; only the outcomes are redrawn, so
    # precompute them once rather than 3000 times
    plan = []
    for nm, test in BANDS:
        si = [(i, grade.american_profit(r["adv_odds"]))
              for i, r in enumerate(recs) if test(r["adv_odds"])]
        oi = [(i, grade.american_profit(r["opp_odds"]))
              for i, r in enumerate(recs) if test(r["opp_odds"])]
        if len(si) >= MIN_CELL and len(oi) >= MIN_CELL:
            plan.append((si, oi))
    probs = [r["p_adv"] for r in recs]

    rng = random.Random(97)
    null = []
    for _ in range(TRIALS):
        # one coin per GAME: redrawing the stat side's outcome sets the
        # opponent's too, which is what makes the delta a real contrast
        flips = [rng.random() < q for q in probs]
        m = None
        for si, oi in plan:
            rs = sum(w if flips[i] else -1 for i, w in si) / len(si)
            ro = sum(-1 if flips[i] else w for i, w in oi) / len(oi)
            m = (rs - ro) if m is None else max(m, rs - ro)
        if m is not None:
            null.append(m * 100)
    p = (sum(1 for x in null if x >= best_d) + 1) / (len(null) + 1) if null else 1.0
    md += ["## Does the best band beat the search that found it?", "",
           f"- best band: **{best_nm}**, delta **{best_d:+.1f} points**",
           f"- bands entering the correction: **{len(live)}**",
           f"- biggest delta a redraw manufactures: median "
           f"**{st.median(null):+.1f}**, 95th pct **{sorted(null)[int(.95*len(null))]:+.1f}**",
           f"- **corrected p = {p:.3f}**", "",
           ("**Clears.** A seven-band scan on price-redrawn outcomes produces a "
            "delta this large less than 5% of the time."
            if p < 0.05 else
            "**Does not clear.** A scan this wide manufactures a delta this "
            "large often enough that the number is the width of the search."),
           ""]

    # --- split-half: does the SHAPE repeat? ---------------------------------
    rh = random.Random(1721)
    half = {i: rh.random() < 0.5 for i in range(len(recs))}
    a = [r for i, r in enumerate(recs) if half[i]]
    b = [r for i, r in enumerate(recs) if not half[i]]
    pairs = []
    md += ["## Does the shape repeat? (split-half)", "",
           "_The test that has actually discriminated here: it killed the team "
           "scan (r=-0.12), the fade profile (r=-0.64) and the stat combos "
           "(r=-0.20), and endorsed near_miss (r=+0.88)._", "",
           "| band | delta, half A | delta, half B |", "|---|---|---|"]
    for name, test in BANDS:
        sa, oa = _stat_side(a, test), _other_side(a, test)
        sb, ob = _stat_side(b, test), _other_side(b, test)
        if min(len(sa), len(oa), len(sb), len(ob)) < MIN_HALF:
            continue
        da, db = (_roi(sa) - _roi(oa)) * 100, (_roi(sb) - _roi(ob)) * 100
        pairs.append((da, db))
        md.append(f"| {name} | {da:+.1f} pts | {db:+.1f} pts |")
    md.append("")
    if len(pairs) >= 4:
        r = st.correlation([x for x, _ in pairs], [y for _, y in pairs])
        md += [f"- **split-half r = {r:+.2f}** over {len(pairs)} bands", "",
               ("_Positive: the price shape the stat model has is at least "
                "partly repeatable, which is more than any other signal tested "
                "here managed._" if r > 0.3 else
                "_Not repeatable. The per-band deltas in one half do not "
                "predict the other, which means the band-to-band pattern is "
                "noise being read as structure._"), ""]
    else:
        md += ["_Too few bands survive both halves at n≥15 to correlate._", ""]

    # --- holdout, and the one signal that has held up -----------------------
    md += ["## The best band over time, and against line movement", ""]
    pre = [x for x in best_s if x["date"] < HOLDOUT_FROM]
    post = [x for x in best_s if x["date"] >= HOLDOUT_FROM]
    md += [f"- **{best_nm}**, stat side, in-sample: {_fmt(pre)}",
           f"- **{best_nm}**, stat side, holdout: {_fmt(post)}", ""]
    ag = [x for x in best_s if x["toward"] is not None and x["toward"] <= -LINE_MIN]
    wi = [x for x in best_s if x["toward"] is not None and x["toward"] >= LINE_MIN]
    fl = [x for x in best_s if x["toward"] is not None
          and -LINE_MIN < x["toward"] < LINE_MIN]
    md += ["_Line movement is the one thing that has held up on this data, so "
           "the question is whether it compounds with the price band or just "
           "overlaps it._", "",
           "| within the best band | stat side |", "|---|---|",
           f"| line moved AGAINST the stat side (≥1.0%) | {_fmt(ag)} |",
           f"| line moved WITH it | {_fmt(wi)} |",
           f"| flat | {_fmt(fl)} |", ""]
    if len(ag) >= MIN_CELL:
        lo = sorted(_redraw_roi(ag, random.Random(200 + k)) for k in range(TRIALS))
        worse = sum(1 for x in lo if x >= _roi(ag)) / len(lo)
        md += [f"- market-calibrated null on that cell: **{worse:.0%}** of "
               "redraws reach or beat it", ""]
    else:
        md += [f"_The line-against cell is n={len(ag)} - reported, not "
               "actionable._", ""]

    md += ["## How to read this", "",
           "- the **delta** column is the only number that isolates the stat "
           "model; the raw band ROI includes whatever the price band did",
           "- a band that clears the permutation but fails split-half is a "
           "cell that got lucky, not a property of price",
           "- nothing here changes the board. The live rule does not consult "
           "`advantage_team` to choose a side - it is a coordinate system for "
           "reading the book, and that stays true whatever this says.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "stat_price.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
