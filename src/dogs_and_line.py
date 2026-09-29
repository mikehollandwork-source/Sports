"""
Good dogs AND the line moved against them - do the two combine?

THE HYPOTHESIS
A team the market usually favours, priced as an underdog, whose price has drifted
LONGER since the open. Each half has something behind it:

  good dogs      +20.2 points against other dogs at the >=70% cut, corrected
                 p = 0.026, split-half +22.9/+17.3 - but +7.5 points outside
                 August, where the dogs themselves sat +0.39 SD above their own
                 price. The difference there was mostly the control losing the
                 vig, not the picks winning.
  line against   the only gate that survived gate_sweep. With no line gate at
                 all the pool returns -1.8%; with any adverse move, +5.9%.

WHY A 2x2 AND NOT ONE CELL
Quoting "good dogs with the line against them" on its own cannot say whether
the combination adds anything. If good dogs return the same with and without the
line condition, the line is doing nothing here; if the line condition works
equally on ordinary dogs, the "good" part is decoration. Only the four cells
together separate those, and the interaction is the claim being made.

WHAT WOULD MAKE THIS FAKE, AND THE TEST FOR EACH
  it is a conjunction chosen after seeing both parts, which is the weakest
  provenance in this whole project. So: permutation with winners redrawn from
  de-vigged prices across every cell, split-half, leave-August-out (good dogs
  were +35.5 in August against +7.0 and +7.3 either side), and month by month.

  n will be small. The >=70% cut had 159 dog games; requiring an adverse move
  cuts that again. A cell under 50 games is reported and not believed, and the
  exact count is printed next to every number so it cannot be read past.

Favourite rate is computed from each team's PRIOR games only, never the season
being scored.

Writes output/dogs_and_line.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("dogs_and_line")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 10000
CUTS = [0.55, 0.60, 0.65, 0.70]
MIN_PRIOR = 20
BELIEVE = 50          # below this a cell is printed but not believed


def collect() -> list[dict]:
    """One row per team-game: the team's price, its de-vigged probability, how
    far the line moved AGAINST it, and whether it won."""
    out = []
    prior = defaultdict(list)
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        day = []
        for g in json.loads(Path(f).read_text()).get("games", []):
            res = results.get(g.get("game_pk"))
            m = g.get("matchup") or ""
            if not res or not res.get("final") or not res.get("winner") or " @ " not in m:
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            away, home = m.split(" @ ")
            if adv not in (away, home) or not isinstance(a_ml, int) \
                    or not isinstance(o_ml, int):
                continue
            opp = home if adv == away else away
            tot = _implied(a_ml) + _implied(o_ml)
            shift = (pc.get("line_check") or {}).get("implied_shift")
            if tot <= 0 or not isinstance(shift, (int, float)):
                continue
            price = {adv: a_ml, opp: o_ml}
            for t in (home, away):
                toward = shift if t == adv else -shift
                hist = prior[t]
                day.append({
                    "date": date, "team": t, "odds": price[t],
                    "p": _implied(price[t]) / tot,
                    "won": res["winner"] == t,
                    "against": -toward,
                    "rate": (sum(hist) / len(hist)) if len(hist) >= MIN_PRIOR else None,
                })
        out += day
        for r in day:                      # update history only after the day
            prior[r["team"]].append(1 if r["odds"] < 0 else 0)
    return out


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1
               for r in rs) / len(rs)


def _fmt(rs) -> str:
    if not rs:
        return "—"
    w = sum(1 for r in rs if r["won"])
    exp = sum(r["p"] for r in rs)
    flag = "" if len(rs) >= BELIEVE else " ⚠"
    return (f"{w}-{len(rs)-w} · exp {exp:.1f} · **{_roi(rs):+.1%}** "
            f"(n={len(rs)}){flag}")


def _boot(rs) -> tuple[float, float]:
    by = defaultdict(list)
    for r in rs:
        by[r["date"]].append(grade.american_profit(r["odds"]) if r["won"] else -1)
    days = sorted(by)
    if len(days) < 5:
        return (float("nan"), float("nan"))
    rng = random.Random(1717)
    out = []
    for _ in range(TRIALS):
        v = []
        for _ in days:
            v += by[days[rng.randrange(len(days))]]
        if v:
            out.append(st.mean(v) * 100)
    out.sort()
    return out[int(.025 * len(out))], out[int(.975 * len(out))]


def build() -> str:
    rows = [r for r in collect() if r["rate"] is not None]
    dogs = [r for r in rows if r["odds"] > 0]
    md = ["# Good dogs and the line moving against them", "",
          "_Each half has something behind it. Good dogs: +20.2 points against "
          "other dogs at the ≥70% cut, corrected p = 0.026 — but +7.5 outside "
          "August, where the dogs themselves were only +0.39 SD above their own "
          "price. Line against: the only gate that survived `gate_sweep` — the "
          "pool returns −1.8% with no line gate and +5.9% with any adverse move._",
          "",
          "_This is a conjunction chosen after seeing both parts, which is the "
          "weakest provenance in the project, so it gets the full battery. And a "
          "2×2 rather than one cell: quoting \"good dogs with the line against "
          "them\" alone cannot say whether the combination adds anything._", "",
          f"- team-games with a prior favourite rate: **{len(rows)}**",
          f"- of those, priced as underdogs: **{len(dogs)}**",
          f"- ⚠ marks a cell under {BELIEVE} games — printed, not believed", ""]
    if len(dogs) < 200:
        return "\n".join(md + ["Not enough underdog games.", ""])

    best_cut, best_n = None, -1
    for cut in CUTS:
        good = [r for r in dogs if r["rate"] >= cut]
        ord_ = [r for r in dogs if r["rate"] < cut]
        md += [f"## Favourite ≥{cut:.0%} of prior games", "",
               "| | line moved AGAINST them | line did not |", "|---|---|---|",
               f"| **good dog** | {_fmt([r for r in good if r['against'] > 0])} | "
               f"{_fmt([r for r in good if r['against'] <= 0])} |",
               f"| ordinary dog | {_fmt([r for r in ord_ if r['against'] > 0])} | "
               f"{_fmt([r for r in ord_ if r['against'] <= 0])} |", ""]
        cell = [r for r in good if r["against"] > 0]
        alone = good
        line_only = [r for r in dogs if r["against"] > 0]
        if cell:
            lo, hi = _boot(cell)
            md += [f"- the combination: {_fmt(cell)}"
                   + ("" if lo != lo else f" · 95% CI {lo:+.1f}% to {hi:+.1f}%"),
                   f"- good dogs **without** the line condition: {_fmt(alone)}",
                   f"- the line condition on **all** dogs: {_fmt(line_only)}",
                   f"- so the line condition adds "
                   f"**{(_roi(cell)-_roi(alone))*100:+.1f} pts** to good dogs, and "
                   f"being a good dog adds "
                   f"**{(_roi(cell)-_roi(line_only))*100:+.1f} pts** to the line "
                   "condition", ""]
            if len(cell) > best_n:
                best_cut, best_n = cut, len(cell)
    # --- the strongest cut, attacked -------------------------------------
    if best_cut is None:
        return "\n".join(md)
    good = [r for r in dogs if r["rate"] >= best_cut]
    cell = [r for r in good if r["against"] > 0]
    # identity, not equality: `r not in cell` compares dicts and would drop
    # any control row that happens to match a cell row field-for-field
    in_cell = {id(r) for r in cell}
    others = [r for r in dogs if id(r) not in in_cell]
    md += [f"## The ≥{best_cut:.0%} combination, attacked", "", ]

    # permutation across all eight cells, one redraw of the dog pool per trial
    pools = []
    for cut in CUTS:
        g = [r for r in dogs if r["rate"] >= cut]
        o = [r for r in dogs if r["rate"] < cut]
        for sub in (g, o):
            for cond in (lambda r: r["against"] > 0, lambda r: r["against"] <= 0):
                c = [r for r in sub if cond(r)]
                if len(c) >= 30:
                    pools.append(c)
    pos = {id(r): i for i, r in enumerate(dogs)}
    idx = [[pos[id(r)] for r in c if id(r) in pos] for c in pools]
    prof = [grade.american_profit(r["odds"]) for r in dogs]
    prob = [r["p"] for r in dogs]
    rng = random.Random(1818)
    hi_d = []
    for _ in range(TRIALS):
        draw = [prof[i] if rng.random() < prob[i] else -1 for i in range(len(dogs))]
        hi_d.append(max(sum(draw[i] for i in ii) / len(ii) for ii in idx if ii) * 100)
    obs = _roi(cell) * 100
    pv = (sum(1 for x in hi_d if x >= obs) + 1) / (TRIALS + 1)
    md += [f"- observed **{obs:+.1f}%** on {len(cell)} games",
           f"- best of {len(pools)} cells on noise reaches "
           f"{st.median(hi_d):+.1f}% median, "
           f"{sorted(hi_d)[int(.95*TRIALS)]:+.1f}% at the 95th",
           f"- **corrected p = {pv:.3f}**", ""]

    rh = random.Random(1919)
    tag = [rh.random() < 0.5 for _ in cell]
    a = [x for x, t in zip(cell, tag) if t]
    b = [x for x, t in zip(cell, tag) if not t]
    if min(len(a), len(b)) >= 15:
        md += [f"- split-half: {_fmt(a)} against {_fmt(b)}",
               "- " + ("**both halves agree in sign**" if (_roi(a) > 0) == (_roi(b) > 0)
                       else "**the halves disagree**"), ""]

    md += ["### Leave August out", "",
           "| period | the combination | all other dogs |", "|---|---|---|"]
    for lab, keep in (("all months", lambda d: True),
                      ("**excluding August**", lambda d: d[:7] != "2026-08"),
                      ("August only", lambda d: d[:7] == "2026-08"),
                      ("September only", lambda d: d[:7] == "2026-09")):
        c = [r for r in cell if keep(r["date"])]
        o = [r for r in others if keep(r["date"])]
        if c:
            md.append(f"| {lab} | {_fmt(c)} | {_fmt(o)} |")
    md.append("")

    ex = [r for r in cell if r["date"][:7] != "2026-08"]
    if ex:
        exp = sum(r["p"] for r in ex)
        act = sum(1 for r in ex if r["won"])
        sd = (len(ex) * (exp / len(ex)) * (1 - exp / len(ex))) ** .5
        z = (act - exp) / sd if sd else 0.0
        md += [f"**Outside August: {act} wins against {exp:.1f} expected on "
               f"{len(ex)} games — {z:+.2f} standard deviations.**",
               "- " + ("that is a real beat of its own price" if z > 2 else
                       "that is indistinguishable from correctly priced, so the "
                       "combination is not adding anything August was not "
                       "already providing"), ""]

    md += ["## The bar", "",
           "- the combination has to beat **good dogs alone** and **the line "
           "condition alone**, or it is not a combination, it is whichever half "
           "is carrying it",
           "- it has to beat its own de-vigged price, not just beat other dogs — "
           "other dogs lose the vig by definition",
           f"- and it has to do it on more than {BELIEVE} games outside August", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "dogs_and_line.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
