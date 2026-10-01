"""
Walk-forward on "line disagrees with handle — bet the money side".

THE CANDIDATE
`line_vs_money` found that when the price moves AWAY from where the dollars are,
backing the dollars went 34-21 (+17.3%) while backing the line side went 21-34
(-23.2%), with the holdout agreeing in direction (+9.8% against -10.2%). It has
a mechanism: a book repricing against its own money is acting on information the
handle does not reflect, and the public dollars are the side being taken.

WHAT THIS CAN AND CANNOT ESTABLISH - READ FIRST
The cell was SELECTED out of roughly twenty configurations in that report, and
every day of data available here was already visible when it was picked. So
there is no genuinely out-of-sample period, and no walk-forward run on this data
can manufacture one. Its p = 0.043 is uncorrected; across twenty cells that is
about p = 0.57.

What a walk-forward CAN do here is answer the question selection bias does not
touch: is the effect spread through time, or is it one stretch? A rule that
pays in most blocks is a rule; one that pays in two blocks and nowhere else is a
stretch wearing a rule's clothes, and that is what killed the gate change, the
good dogs and the dogs-and-line conjunction.

It also fits the one free parameter honestly. The minimum line move was set at
1% in the original report with no justification given, so here it is CHOSEN on
past blocks only and scored on the next, which is a real fit-and-test even if
the cell's selection is not.

Writes output/line_money_walk.md.
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

log = logging.getLogger("line_money_walk")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 10000
THRESHOLDS = [0.005, 0.01, 0.02, 0.03]
BLOCK = 10
MIN_TRAIN = 25


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
            m = g.get("matchup") or ""
            if not res or not res.get("final") or not res.get("winner") or " @ " not in m:
                continue
            pc = g.get("pick_criteria") or {}
            chk = g.get("public_check") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            shift = (pc.get("line_check") or {}).get("implied_shift")
            ms = chk.get("money_side")
            away, home = m.split(" @ ")
            if adv not in (away, home) or not isinstance(a_ml, int) \
                    or not isinstance(o_ml, int) or not isinstance(shift, (int, float)) \
                    or ms not in ("home", "away"):
                continue
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            money_team = home if ms == "home" else away
            if money_team not in price:
                continue
            # shift is signed TOWARD the advantage side
            line_team = adv if shift > 0 else opp if shift < 0 else None
            if line_team is None:
                continue
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue
            rows.append({
                "date": date, "move": abs(shift),
                "disagree": line_team != money_team,
                "money_team": money_team, "money_odds": price[money_team],
                "money_won": res["winner"] == money_team,
                "line_odds": price[line_team],
                "line_won": res["winner"] == line_team,
                "p": _implied(price[money_team]) / tot,
            })
    return rows


def _roi(rs, odds="money_odds", won="money_won") -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r[odds]) if r[won] else -1 for r in rs) / len(rs)


def _fmt(rs, odds="money_odds", won="money_won") -> str:
    if not rs:
        return "— (0)"
    w = sum(1 for r in rs if r[won])
    return f"{w}-{len(rs)-w} · **{_roi(rs, odds, won):+.1%}** (n={len(rs)})"


def _sel(rs, thr):
    return [r for r in rs if r["disagree"] and r["move"] >= thr]


def build() -> str:
    rows = collect()
    md = ["# Walk-forward: line disagrees with handle, bet the money side", "",
          "_`line_vs_money` had this at 34-21 (+17.3%) backing the dollars "
          "against 21-34 (−23.2%) backing the line side, holdout agreeing in "
          "direction. It has a mechanism — a book repricing against its own "
          "money is acting on information the handle does not reflect._", "",
          "_**What this cannot establish.** The cell was selected out of ~20 "
          "configurations, and every day of data here was already visible when "
          "it was picked, so no genuinely out-of-sample period exists and no "
          "walk-forward can create one. Its p = 0.043 is uncorrected; across "
          "twenty cells that is roughly 0.57._", "",
          "_**What it can.** Whether the effect is spread through time or is one "
          "stretch — the question selection bias does not touch, and the one "
          "that killed the gate change, the good dogs and the dogs-and-line "
          "conjunction._", "",
          f"- graded games with a line move, a handle side and prices: "
          f"**{len(rows)}**", ""]
    if len(rows) < 200:
        return "\n".join(md + ["Too few games.", ""])

    dis = [r for r in rows if r["disagree"]]
    agr = [r for r in rows if not r["disagree"]]
    md += ["## The whole sample, for reference", "",
           "| | bet the money side | bet the line side |", "|---|---|---|",
           f"| line DISAGREES with handle | {_fmt(dis)} | "
           f"{_fmt(dis, 'line_odds', 'line_won')} |",
           f"| line AGREES with handle | {_fmt(agr)} | "
           f"{_fmt(agr, 'line_odds', 'line_won')} |", ""]

    # ---- block by block, rule fixed -------------------------------------
    days = sorted({r["date"] for r in rows})
    blocks = []
    for i in range(0, len(days) - BLOCK + 1, BLOCK):
        ds = set(days[i:i + BLOCK])
        sub = _sel([r for r in rows if r["date"] in ds], 0.01)
        if len(sub) >= 3:
            blocks.append((days[i], sub))
    md += ["## Block by block, rule fixed at the original ≥1% bar", "",
           "_Is it spread through time, or one stretch?_", "",
           "| block starts | money side | n |", "|---|---|---|"]
    wins = 0
    for start, sub in blocks:
        r = _roi(sub)
        wins += r > 0
        md.append(f"| {start} | {r:+.1%} | {len(sub)} |")
    md.append("")
    if blocks:
        md += [f"- profitable blocks: **{wins}/{len(blocks)}** · median block "
               f"**{st.median([_roi(s) for _, s in blocks]):+.1%}**",
               "- " + ("**spread through time**, not one stretch"
                       if wins >= len(blocks) * 0.6 else
                       "**concentrated.** Most blocks do not pay, so the pooled "
                       "number is carried by a few — the shape that has failed "
                       "every other candidate here"), ""]

    # ---- the threshold, chosen on past blocks only ----------------------
    picked, oos = [], []
    i = MIN_TRAIN
    while i < len(days):
        train = {d for d in days[:i]}
        test = {d for d in days[i:i + BLOCK]}
        tr = [r for r in rows if r["date"] in train]
        te = [r for r in rows if r["date"] in test]
        best = max(THRESHOLDS, key=lambda t: _roi(_sel(tr, t)))
        picked.append(best)
        oos += _sel(te, best)
        i += BLOCK
    md += ["## Fitting the one free parameter honestly", "",
           "_The 1% bar was set with no justification given. Here it is chosen "
           "on past blocks only and scored on the next._", "",
           "- thresholds chosen: " + ", ".join(
               f"{t:.1%}×{picked.count(t)}" for t in THRESHOLDS if picked.count(t)),
           f"- **out-of-sample: {_fmt(oos)}**", ""]
    scored = set()
    i = MIN_TRAIN
    while i < len(days):
        scored |= set(days[i:i + BLOCK])
        i += BLOCK
    pool = [r for r in rows if r["date"] in scored]
    md += ["| fixed bar over the same days | money side |", "|---|---|"]
    for t in THRESHOLDS:
        md.append(f"| ≥{t:.1%} | {_fmt(_sel(pool, t))} |")
    md.append("")

    # ---- bootstrap on the difference against the agreeing pool ----------
    d_sel = _sel(rows, 0.01)
    ctrl = [r for r in agr if r["move"] >= 0.01]
    if len(d_sel) >= 30 and len(ctrl) >= 30:
        by_d, by_c = defaultdict(list), defaultdict(list)
        for r in d_sel:
            by_d[r["date"]].append(grade.american_profit(r["money_odds"])
                                   if r["money_won"] else -1)
        for r in ctrl:
            by_c[r["date"]].append(grade.american_profit(r["money_odds"])
                                   if r["money_won"] else -1)
        allday = sorted(set(by_d) | set(by_c))
        rng = random.Random(9090)
        diffs = []
        for _ in range(TRIALS):
            a, b = [], []
            for _ in allday:
                dd = allday[rng.randrange(len(allday))]
                a += by_d.get(dd, []); b += by_c.get(dd, [])
            if a and b:
                diffs.append((st.mean(a) - st.mean(b)) * 100)
        diffs.sort()
        obs = (_roi(d_sel) - _roi(ctrl)) * 100
        md += ["## Against the agreeing pool, day-block bootstrapped", "",
               f"- disagree: {_fmt(d_sel)} · agree: {_fmt(ctrl)}",
               f"- difference **{obs:+.1f} pts** · 95% CI "
               f"**{diffs[int(.025*len(diffs))]:+.1f} to "
               f"{diffs[int(.975*len(diffs))]:+.1f}**", ""]
    md += ["## The bar", "",
           "- spread across blocks, an out-of-sample threshold choice that does "
           "not fall apart, and a difference whose interval clears zero",
           "- none of which fixes the selection. Only games played AFTER today "
           "can do that", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "line_money_walk.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
