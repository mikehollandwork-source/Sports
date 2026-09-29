"""
What do winning underdogs have in common?

THE QUESTION AND ITS TRAP
Every underdog in the dataset is profiled against everything we record - line
movement, stat margin, form, BvP, park, umpire, weather, records, public %,
price, home/away - to find what separates the ones that win.

The trap is that "what do the winners have in common" is a post-hoc question
over ~20 features and ~50 buckets. Scan that many cells against a coin flip and
several will look excellent. That is precisely how the +40% dog-money cell
happened, and it did not survive.

THE CORRECTION
So the headline test here is not "is the best cell good?" but "is the best cell
better than the best cell a SCAN OF THIS SIZE produces by chance?" - a
max-statistic permutation test. Outcomes are redrawn from each game's de-vigged
market price (so favourites still win at the right rate), every cell is
recomputed, and the BEST ROI across all of them is recorded. Repeating that
builds the distribution of "best cell found while scanning noise". The real best
cell is then read against that distribution.

A cell clearing this bar is genuinely interesting. A cell that looks great but
sits inside the null's range is what scanning produces, no matter how good the
story attached to it sounds.

Every cell also carries its holdout split, and cells under MIN_CELL are not
reported at all.

Writes output/dog_profile.md. Reporting only.
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

log = logging.getLogger("dog_profile")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MIN_CELL = 25
TRIALS = 2000


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _feats(g: dict, dog: str, fav: str, dog_home: bool) -> dict:
    """Everything we record, oriented toward the DOG."""
    pc = g.get("pick_criteria") or {}
    f: dict = {"dog_home": dog_home}

    sa = g.get("statistical_advantage") or {}
    hs, as_ = _num(sa.get("home_score")), _num(sa.get("away_score"))
    if hs is not None and as_ is not None:
        f["stat_margin_to_dog"] = (hs - as_) if dog_home else (as_ - hs)
        f["stat_edge_is_dog"] = (sa.get("team") == dog)

    shift = (pc.get("line_check") or {}).get("implied_shift")
    if _num(shift) is not None:
        adv = pc.get("advantage_team")
        f["line_toward_dog"] = shift if adv == dog else -shift

    form = g.get("form") or {}
    hd = _num((form.get("home") or {}).get("delta"))
    ad = _num((form.get("away") or {}).get("delta"))
    if hd is not None and ad is not None:
        f["form_delta_to_dog"] = (hd - ad) if dog_home else (ad - hd)

    bp = g.get("bvp_pen") or {}
    if bp.get("edge_team"):
        f["bvp_edge_is_dog"] = (bp["edge_team"] == dog)
    if _num(bp.get("gap")) is not None:
        f["bvp_gap"] = bp["gap"]

    bv = g.get("bvp") or {}
    ho, ao = _num(bv.get("home_ops")), _num(bv.get("away_ops"))
    if ho is not None and ao is not None:
        f["bvp_ops_to_dog"] = (ho - ao) if dog_home else (ao - ho)

    sit = g.get("situational") or {}
    def _wp(side):
        d = sit.get(side) or {}
        w, l = _num(d.get("wins")), _num(d.get("losses"))
        return w / (w + l) if w is not None and l is not None and (w + l) else None
    hw, aw = _wp("home"), _wp("away")
    if hw is not None and aw is not None:
        f["record_gap_to_dog"] = (hw - aw) if dog_home else (aw - hw)

    if _num(g.get("park_factor")) is not None:
        f["park_factor"] = g["park_factor"]
    ut = g.get("ump_tend") or {}
    for k in ("r_pg", "k_pg"):
        if _num(ut.get(k)) is not None:
            f[f"ump_{k}"] = ut[k]
    w = g.get("weather") or {}
    for k in ("temp_f", "wind_mph"):
        if _num(w.get(k)) is not None:
            f[k] = w[k]

    for k in ("form_gap", "consistency_hits", "sp_dog_edge", "confidence",
              "signals_hit"):
        if _num(pc.get(k)) is not None:
            f[k] = pc[k]
    for k in ("pitching_dog", "edge_strong", "form_edge"):
        if isinstance(pc.get(k), bool):
            f[k] = pc[k]

    wp = _num(pc.get("win_prob"))
    if wp is not None:
        f["model_winprob_dog"] = wp if pc.get("advantage_team") == dog else 100 - wp

    bl = g.get("betting_lines") or {}
    for slot in ("majority", "non_majority"):
        d = bl.get(slot) or {}
        if d.get("team") == dog and _num(d.get("consensus_pct")) is not None:
            f["public_pct_on_dog"] = d["consensus_pct"]
    return f


def collect() -> list:
    recs = []
    for path in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(path).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for g in json.loads(Path(path).read_text()).get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            matchup = g.get("matchup") or ""
            if " @ " not in matchup:
                continue
            away, home = matchup.split(" @ ")
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            dogs = [t for t, ml in price.items() if ml > 0]
            if len(dogs) != 1:
                continue                     # pick'em or both negative - skip
            dog = dogs[0]
            fav = opp if dog == adv else adv
            recs.append({
                "date": date, "dog": dog, "odds": price[dog],
                "won": res["winner"] == dog,
                # the other side of the same game, so a losing dog cell can be
                # priced as a favourite bet rather than assumed to be one
                "fav_odds": price[fav], "fav_won": res["winner"] == fav,
                "p": _implied(price[dog]) / (_implied(a_ml) + _implied(o_ml)),
                "feats": _feats(g, dog, fav, dog == home),
            })
    return recs


def _cells(recs: list) -> dict:
    """{cell_label: [indices]} - binary features split two ways, numeric into
    terciles, so every game lands in exactly one bucket per feature."""
    names = sorted({k for r in recs for k in r["feats"]})
    out: dict = {}
    for nm in names:
        vals = [(i, r["feats"].get(nm)) for i, r in enumerate(recs)]
        have = [(i, v) for i, v in vals if v is not None]
        if len(have) < MIN_CELL * 2:
            continue
        if all(isinstance(v, bool) for _i, v in have):
            for flag in (True, False):
                idx = [i for i, v in have if v is flag]
                if len(idx) >= MIN_CELL:
                    out[f"{nm} = {flag}"] = idx
        else:
            nums = sorted(v for _i, v in have)
            lo, hi = nums[len(nums) // 3], nums[2 * len(nums) // 3]
            if lo == hi:
                continue
            for lab, test in (("low", lambda v: v <= lo),
                              ("mid", lambda v: lo < v <= hi),
                              ("high", lambda v: v > hi)):
                idx = [i for i, v in have if test(v)]
                if len(idx) >= MIN_CELL:
                    out[f"{nm} {lab}"] = idx
    return out


def _roi(recs, idx, wins=None) -> float:
    if not idx:
        return 0.0
    u = 0.0
    for i in idx:
        won = recs[i]["won"] if wins is None else wins[i]
        u += grade.american_profit(recs[i]["odds"]) if won else -1
    return u / len(idx)


def _fmt(recs, idx) -> str:
    if not idx:
        return "—"
    w = sum(1 for i in idx if recs[i]["won"])
    u = sum(grade.american_profit(recs[i]["odds"]) if recs[i]["won"] else -1
            for i in idx)
    return f"{w}-{len(idx)-w} ({w/len(idx):.0%}) · {u:+.1f}u · **{u/len(idx):+.1%}** (n={len(idx)})"


def _fmt_fav(recs, idx) -> str:
    """Backing the FAVOURITE in the same games - what 'fade this dog cell'
    actually pays, rather than what a losing dog ROI implies it pays."""
    if not idx:
        return "—"
    w = sum(1 for i in idx if recs[i]["fav_won"])
    u = sum(grade.american_profit(recs[i]["fav_odds"]) if recs[i]["fav_won"] else -1
            for i in idx)
    return f"{w}-{len(idx)-w} ({w/len(idx):.0%}) · {u:+.1f}u · **{u/len(idx):+.1%}** (n={len(idx)})"


def build() -> str:
    recs = collect()
    md = ["# What do winning underdogs have in common?", "",
          "_Every underdog in the dataset, profiled against everything we "
          "record. The headline is not the best cell — it is whether the best "
          "cell beats what a scan of this size finds in noise._", ""]
    if len(recs) < MIN_CELL * 2:
        return "\n".join(md + ["Too few underdog games.", ""])

    all_idx = list(range(len(recs)))
    wins = sum(1 for r in recs if r["won"])
    md += ["## Baseline", "",
           f"- underdog games: **{len(recs)}**",
           f"- backing every underdog: {_fmt(recs, all_idx)}",
           f"- raw underdog win rate: **{wins/len(recs):.1%}**", ""]

    cells = _cells(recs)
    md += [f"- features scanned: **{len({c.rsplit(' ', 1)[0].split(' =')[0] for c in cells})}**, "
           f"cells (min n={MIN_CELL}): **{len(cells)}**", ""]
    if not cells:
        return "\n".join(md + ["No cell reached the minimum size.", ""])

    ranked = sorted(cells.items(), key=lambda kv: _roi(recs, kv[1]), reverse=True)
    md += ["## Best and worst cells", "",
           "| cell | all underdogs in it | in-sample | holdout |",
           "|---|---|---|---|"]
    for label, idx in ranked[:10] + ranked[-5:]:
        pre = [i for i in idx if recs[i]["date"] < HOLDOUT_FROM]
        post = [i for i in idx if recs[i]["date"] >= HOLDOUT_FROM]
        md.append(f"| `{label}` | {_fmt(recs, idx)} | {_fmt(recs, pre)} | "
                  f"{_fmt(recs, post)} |")
    md.append("")

    # ---- permutation: how extreme are the BEST and WORST cells in pure noise? ----
    # Both tails are tested. Scanning 60+ cells throws up extreme NEGATIVES as
    # readily as extreme positives, and treating an untested negative cell as
    # real - then reversing it - is exactly what produced the reversal rule that
    # went 5-11 / -41% live.
    best_label, best_idx = ranked[0]
    worst_label, worst_idx = ranked[-1]
    best_roi, worst_roi = _roi(recs, best_idx), _roi(recs, worst_idx)
    rng = random.Random(23)
    null_max, null_min = [], []
    for _ in range(TRIALS):
        w = [rng.random() < r["p"] for r in recs]
        rois = [_roi(recs, idx, w) for idx in cells.values()]
        null_max.append(max(rois))
        null_min.append(min(rois))
    beats = sum(1 for m in null_max if m >= best_roi)
    beats_lo = sum(1 for m in null_min if m <= worst_roi)
    null_max.sort()
    null_min.sort()

    md += ["## The test that matters", "",
           f"Best cell: `{best_label}` at **{best_roi:+.1%}**.", "",
           "_Outcomes redrawn {t} times from each game's de-vigged market price, "
           "every cell recomputed, and the BEST cell recorded each time — the "
           "distribution of 'best result found while scanning noise'._"
           .format(t=TRIALS), "",
           f"- median best-in-noise: **{st.median(null_max):+.1%}**",
           f"- 95th percentile of best-in-noise: **{null_max[int(.95*TRIALS)]:+.1%}**",
           f"- our best cell: **{best_roi:+.1%}**",
           f"- **corrected p = {beats/TRIALS:.3f}**", ""]

    if beats / TRIALS <= 0.05:
        md += ["**This clears the bar.** The best cell is better than a scan of "
               "this size produces by chance. Worth a holdout-forward trial.", ""]
    else:
        md += ["**This does not clear the bar.** A scan of this many cells finds "
               "something this good in noise more than 5% of the time, so the "
               "headline number is what the search produced, not what the data "
               "contains. Whatever story fits the best cell, it is not evidence.",
               ""]

    # ---- the other tail, and what fading it actually pays ----
    md += ["## The other tail — are the LOSING cells real?", "",
           f"Worst cell: `{worst_label}` at **{worst_roi:+.1%}**.", "",
           f"- median worst-in-noise: **{st.median(null_min):+.1%}**",
           f"- 5th percentile of worst-in-noise: **{null_min[int(.05*TRIALS)]:+.1%}**",
           f"- our worst cell: **{worst_roi:+.1%}**",
           f"- **corrected p = {beats_lo/TRIALS:.3f}**", ""]
    if beats_lo / TRIALS <= 0.05:
        md += ["**The losing tail clears the bar** — this cell is worse than a "
               "scan of this size manufactures. That makes it a real avoid.", ""]
    else:
        md += ["**The losing tail does not clear either.** A scan this wide "
               "produces cells this bad in noise routinely, so the losing cells "
               "are no more real than the winning ones — and reversing them "
               "would be betting on the search, not the data.", ""]

    md += ["### Fading the worst cells — what it actually pays", "",
           "_A dog cell losing 20% does NOT mean backing the favourite there "
           "wins 20%; the favourite is priced too. This is the same games, "
           "betting the other side._", "",
           "| cell | backing the dog | backing the FAVOURITE instead |",
           "|---|---|---|"]
    for label, idx in ranked[-5:]:
        md.append(f"| `{label}` | {_fmt(recs, idx)} | {_fmt_fav(recs, idx)} |")
    md += ["", f"_For reference, backing the favourite in every underdog game: "
           f"{_fmt_fav(recs, all_idx)}._", ""]

    md += ["## Reading the cells above", "",
           "A cell is only interesting if it is strong all-time AND holds in the "
           "holdout column AND the corrected p above clears. Any one of those "
           "alone is the pattern that has failed repeatedly here.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "dog_profile.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
