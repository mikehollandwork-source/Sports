"""
Margin and form together - as strengths, not as flags.

WHAT WAS ALREADY TESTED, AND WHY IT ISN'T THIS
`stat_combos` paired every stat as a BINARY: does this stat favour the stat side
or not. `margin` + `form` both favouring returned -6% over 237 games, and the
27-signal log-loss model found no information in any combination. That is a real
answer to a narrower question.

Two things it could not see:

  1. MAGNITUDE. Both inputs have a size, and the flag throws it away. A game
     where the index gap is enormous and the bats are scorching is filed
     identically to one where both are barely positive. If the pair carries
     anything, the strong corner is where it lives.
  2. PRICE CONFOUNDING. A big index gap and hot bats both push a team toward
     being a favourite, so "both favour" is partly a price bucket wearing a
     stat costume. `stat_price` showed how much that matters: the stat model's
     apparent dog edge shrank from +14.2% to +11.6 points once the same prices
     were held on the other side, and the favourite bands flipped sign entirely.

So this reads both as continuous strengths, tiers them by their own
distributions, and controls for price by STRATIFICATION: within each price band,
compare the stat side when the conjunction holds against the stat side when it
does not, then weight the within-band differences by the conjunction's own band
counts. That difference cannot be a price effect, because price is held fixed
inside every term of it.

THREE READINGS OF FORM, because the first one used here was wrong once before
  team delta   form.{home,away}.delta - the team-wide form swing
  hot bats     the SUM of form.hot deltas, which is what `hot_home_dog` had to
               switch to after "does the team have at least as many hot bats"
               turned out to be vacuous: form.hot is a fixed top-2 list, so the
               comparison was a tie that resolved true on 77 of 84 games
  either       whichever of the two is larger, to avoid choosing after the fact

Pre-registered: max-statistic permutation across the tier x form-reading grid,
split-half reliability on the tier ladder, holdout split, and the crossing with
line movement at the live board's threshold.

THE PRIOR, STATED BEFORE THE RESULT
Every one of the eight items in that list has now been tested alone, in pairs,
in all 127 subsets, by price band, against a same-price control, and as a
deviation from the market. All null. If the strong corner of margin x form is
real it will clear a permutation and repeat across halves; nothing else in this
family has done both, and I do not expect this to either.

Writes output/margin_form.md.
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

log = logging.getLogger("margin_form")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MIN_CELL = 30
MIN_HALF = 15
TRIALS = 3000
LINE_MIN = 0.01

BANDS = [
    ("≤-200", lambda o: o <= -200),
    ("-199..-140", lambda o: -199 <= o <= -140),
    ("-139..-110", lambda o: -139 <= o <= -110),
    ("-109..+109", lambda o: -109 <= o <= 109),
    ("+110..+139", lambda o: 110 <= o <= 139),
    ("≥+140", lambda o: o >= 140),
]
FORMS = ["team delta", "hot bats", "either"]
TIERS = [("both above median", 0.50), ("both top third", 0.667),
         ("both top quartile", 0.75)]


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
            form = g.get("form") or {}
            fh, fa = form.get("home") or {}, form.get("away") or {}
            dh, da = fh.get("delta"), fa.get("delta")
            if (not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int)
                    or not isinstance(hs, (int, float))
                    or not isinstance(as_, (int, float))
                    or not isinstance(dh, (int, float))
                    or not isinstance(da, (int, float))):
                continue
            away, home = m.split(" @ ")
            adv_home = adv == home
            margin = (hs - as_) if adv_home else (as_ - hs)
            team_gap = (dh - da) if adv_home else (da - dh)
            hot_h = sum(p.get("delta", 0) for p in (fh.get("hot") or []))
            hot_a = sum(p.get("delta", 0) for p in (fa.get("hot") or []))
            hot_gap = (hot_h - hot_a) if adv_home else (hot_a - hot_h)
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue
            recs.append({
                "date": date, "odds": a_ml, "opp_odds": o_ml,
                "won": res["winner"] == adv,
                "margin": margin, "team delta": team_gap, "hot bats": hot_gap,
                "either": max(team_gap, hot_gap),
                "p": _implied(a_ml) / tot,
                "toward": (pc.get("line_check") or {}).get("implied_shift"),
            })
    return recs


def _roi(rows) -> float:
    if not rows:
        return 0.0
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1
               for r in rows) / len(rows)


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w = sum(1 for r in rows if r["won"])
    u = sum(grade.american_profit(r["odds"]) if r["won"] else -1 for r in rows)
    tail = "" if len(rows) >= MIN_CELL else " _(thin)_"
    return f"{w}-{len(rows)-w} · {u:+.1f}u · **{_roi(rows):+.1%}** (n={len(rows)}){tail}"


def _q(vals: list[float], q: float) -> float:
    s = sorted(vals)
    return s[min(int(q * len(s)), len(s) - 1)]


def _strat_delta(hit, miss) -> tuple[float, int]:
    """Conjunction minus non-conjunction, computed INSIDE each price band and
    then weighted by the conjunction's own band counts. Price is held fixed in
    every term, so the result cannot be a price effect.

    Returns (delta in points, games contributing)."""
    num = den = 0.0
    used = 0
    for _, test in BANDS:
        h = [r for r in hit if test(r["odds"])]
        m = [r for r in miss if test(r["odds"])]
        if len(h) < 8 or len(m) < 8:
            continue
        num += len(h) * (_roi(h) - _roi(m))
        den += len(h)
        used += len(h)
    return ((num / den * 100) if den else 0.0), used


def build() -> str:
    recs = collect()
    md = ["# Margin and form together, as strengths rather than flags", "",
          "_`stat_combos` already paired these as binaries - both favouring the "
          "stat side returned -6% over 237 games. That test threw away both "
          "magnitudes and did not control for price, and a big index gap plus "
          "hot bats both push a team toward being a favourite, so \"both "
          "favour\" is partly a price bucket in a stat costume. Here both are "
          "read as continuous strengths and price is held fixed by "
          "stratification._", "",
          f"- graded games with an index gap and a form read: **{len(recs)}**", ""]
    if len(recs) < 200:
        return "\n".join(md + ["Not enough graded games.", ""])

    for i, r in enumerate(recs):
        r["_i"] = i
    margins = [r["margin"] for r in recs]

    def cell(form: str, q: float) -> tuple[list, list]:
        mc, fc = _q(margins, q), _q([r[form] for r in recs], q)
        hit = [r for r in recs if r["margin"] >= mc and r[form] >= fc]
        miss = [r for r in recs if not (r["margin"] >= mc and r[form] >= fc)]
        return hit, miss

    md += ["## The strong corner, by how form is read", "",
           "_Backing the stat side when BOTH the index gap and the form gap "
           "clear the same percentile. `delta` is the price-stratified "
           "difference against the stat side in games that miss the "
           "conjunction - the number that is not a price effect._", "",
           "| tier | form read | back the stat side | price-stratified delta |",
           "|---|---|---|---|"]
    grid = []
    for tname, q in TIERS:
        for form in FORMS:
            hit, miss = cell(form, q)
            d, used = _strat_delta(hit, miss)
            grid.append((tname, form, hit, d))
            md.append(f"| {tname} | {form} | {_fmt(hit)} | "
                      f"**{d:+.1f} pts** ({used} matched) |")
    md.append("")

    md += [f"_Baseline for comparison: backing the stat side in every game is "
           f"{_fmt(recs)}._", ""]

    # --- correction for the 9-cell scan ------------------------------------
    live = [(t, f, h, d) for t, f, h, d in grid if len(h) >= MIN_CELL]
    if not live:
        return "\n".join(md + ["No tier reaches n=30.", ""])
    bt, bf, bh, bd = max(live, key=lambda x: x[3])
    probs = [r["p"] for r in recs]
    plans = []
    for tname, q in TIERS:
        for form in FORMS:
            hit, miss = cell(form, q)
            if len(hit) < MIN_CELL:
                continue
            idx = {id(r) for r in hit}
            per_band = []
            for _, test in BANDS:
                h = [r for r in recs if id(r) in idx and test(r["odds"])]
                m = [r for r in recs if id(r) not in idx and test(r["odds"])]
                if len(h) < 8 or len(m) < 8:
                    continue
                per_band.append((
                    [(r["_i"], grade.american_profit(r["odds"])) for r in h],
                    [(r["_i"], grade.american_profit(r["odds"])) for r in m]))
            if per_band:
                plans.append(per_band)
    rng = random.Random(404)
    null, null_min = [], []
    for _ in range(TRIALS):
        flips = [rng.random() < p for p in probs]
        best = worst = None
        for per_band in plans:
            num = den = 0.0
            for h, m in per_band:
                rh = sum(w if flips[i] else -1 for i, w in h) / len(h)
                rm = sum(w if flips[i] else -1 for i, w in m) / len(m)
                num += len(h) * (rh - rm)
                den += len(h)
            v = (num / den * 100) if den else 0.0
            best = v if best is None else max(best, v)
            worst = v if worst is None else min(worst, v)
        if best is not None:
            null.append(best)
            null_min.append(worst)
    p = (sum(1 for x in null if x >= bd) + 1) / (len(null) + 1) if null else 1.0
    md += ["## Does the best corner beat the search that found it?", "",
           f"- best: **{bt} / {bf}**, price-stratified delta **{bd:+.1f} pts**",
           f"- cells entering the correction: **{len(plans)}**",
           f"- biggest a redraw manufactures: median **{st.median(null):+.1f}**, "
           f"95th pct **{sorted(null)[int(.95*len(null))]:+.1f}**",
           f"- **corrected p = {p:.3f}**", "",
           ("**Clears the scan.**" if p < 0.05
            else "**Does not clear the scan.**"), ""]

    # --- the other direction, paid for separately ---------------------------
    # Every cell above came out negative, so the honest follow-up is whether
    # FADING the strong corner is a play. Choosing that direction after seeing
    # the signs is exactly how the underdog scan's "fade the losing cell" error
    # happened, so it gets its own correction: the MOST NEGATIVE delta a redraw
    # manufactures across the same nine cells. Same scan, other tail.
    wt, wf, wh, wd = min(live, key=lambda x: x[3])
    p_fade = ((sum(1 for x in null_min if x <= wd) + 1) / (len(null_min) + 1)
              if null_min else 1.0)
    fade_rows = [{"odds": r["opp_odds"], "won": not r["won"], "date": r["date"],
                  "toward": r["toward"]} for r in wh]
    md += ["## The other direction - is fading the strong corner a play?", "",
           f"- worst cell: **{wt} / {wf}**, price-stratified delta "
           f"**{wd:+.1f} pts** on n={len(wh)}",
           f"- backing the OTHER team in those games: {_fmt(fade_rows)}",
           f"- most negative delta a redraw manufactures: median "
           f"**{st.median(null_min):+.1f}**, 5th pct "
           f"**{sorted(null_min)[int(.05*len(null_min))]:+.1f}**",
           f"- **corrected p (min-statistic) = {p_fade:.3f}**", "",
           ("**The fade clears its own scan.** Worth a shadow ledger, not a "
            "board change - and note the direction was chosen after seeing the "
            "signs, which the correction accounts for but a forward record "
            "would settle properly."
            if p_fade < 0.05 and _roi(fade_rows) > 0 else
            "**The fade does not clear.** Nine cells scanned on redrawn "
            "outcomes produce a cell this bad often enough that its badness is "
            "the width of the search - and picking the direction after seeing "
            "the signs is the error the underdog scan already made once."), ""]

    # --- split-half on the tier ladder -------------------------------------
    rh = random.Random(31)
    tag = [rh.random() < 0.5 for _ in recs]
    pairs = []
    md += ["## Does the ladder repeat? (split-half)", "",
           "| tier / form | half A | half B |", "|---|---|---|"]
    for tname, q in TIERS:
        for form in FORMS:
            hit, _ = cell(form, q)
            idx = {id(r) for r in hit}
            a = [r for i, r in enumerate(recs) if tag[i] and id(r) in idx]
            b = [r for i, r in enumerate(recs) if not tag[i] and id(r) in idx]
            if min(len(a), len(b)) < MIN_HALF:
                continue
            pairs.append((_roi(a) * 100, _roi(b) * 100))
            md.append(f"| {tname} / {form} | {_roi(a):+.1%} | {_roi(b):+.1%} |")
    md.append("")
    if len(pairs) >= 4:
        r = st.correlation([x for x, _ in pairs], [y for _, y in pairs])
        md += [f"- **split-half r = {r:+.2f}** over {len(pairs)} cells", "",
               ("_Positive: the conjunction's ladder is at least partly "
                "repeatable._" if r > 0.3 else
                "_Not repeatable. The strong corner in one half does not "
                "predict the other._"), ""]
    else:
        md += ["_Too few cells survive both halves to correlate._", ""]

    # --- time split and the one signal that has held up --------------------
    pre = [r for r in bh if r["date"] < HOLDOUT_FROM]
    post = [r for r in bh if r["date"] >= HOLDOUT_FROM]
    ag = [r for r in bh if isinstance(r["toward"], (int, float))
          and r["toward"] <= -LINE_MIN]
    wi = [r for r in bh if isinstance(r["toward"], (int, float))
          and r["toward"] >= LINE_MIN]
    md += [f"## The best corner ({bt} / {bf}) over time and against the line", "",
           f"- in-sample: {_fmt(pre)}", f"- holdout: {_fmt(post)}", "",
           f"- line moved AGAINST the stat side: {_fmt(ag)}",
           f"- line moved WITH it: {_fmt(wi)}", "",
           "_If these two are similar, the split is not the price discount - it "
           "is 'the line moved at all', which in this dataset tracks data "
           "availability more than anything about the game. That trap was "
           "walked into once already in `stat_price`._", "",
           "## How to read this", "",
           "- the **delta** column is the only one that isolates the "
           "conjunction; the raw ROI still contains whatever its price mix did",
           "- a corner that clears the permutation but fails split-half is a "
           "cell that got lucky",
           "- the board does not consult margin or form to choose a side, and "
           "nothing here changes that on its own.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "margin_form.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
