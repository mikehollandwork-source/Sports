"""
Does the consensus side being BETTER ON RECORD add anything to the rule?

WHERE THIS CAME FROM
The multi-season base rates showed favourites against sub-.400 teams win
59.7%, short of what -180 demands. Applied to our own settled picks, opponent
quality split them hard: picks where our side was better by more than .100 in
win% went 30-10 (+23.8%), against 31-30 (-8.2%) when the teams were close.

The obvious objection is that the gap is just the price wearing a different
hat - r(gap, odds) = -0.61, and 98% of big-gap picks were favourites. But it
survived holding price constant, in the same direction in both bands:

    favourites <= -150    gap > +.10  +28.5% (18)   gap <= +.10   -1.1% (13)
    mild favs -149..-101  gap > +.10  +25.7% (21)   gap <= +.10  -10.9% (39)

Two independent price bands, ~30 points of separation each, same sign. No
other candidate this season has replicated across an independent split.

WHY THIS FILE AND NOT THAT TABLE
Those cells are 18 and 21 games, chosen after looking, out of our own 104
bets. This runs the same question on every CONSENSUS-QUALIFYING game - the
games the rule would have considered, bet or not - which is roughly nine
times the sample and is not selected on the outcome of our betting.

    1. the gap, on all qualifying games, backing the consensus side
    2. the same, within price bands, since that is the confound
    3. a time holdout - does it hold in the half of the season it was not
       noticed in
    4. split-half, and a permutation across every cell reported

If it survives all four it is the first thing this season to do so, and it
would be a candidate for a SEVENTH gate. If it fails any, it joins the other
thirty-odd, and the price control passing twice was luck.

Writes output/quality_gate.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("quality_gate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 3000
MIN_CELL = 30
MIN_HALF = 12
GAP_HI = 0.10
RULE_LIVE = "2026-07-28"       # the consensus rule's start
HOLDOUT = "2026-09-01"


def collect() -> list[dict]:
    """Every game the consensus rule would have considered: handle agreeing
    with tickets and a readable majority. Bet or not."""
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
            chk = g.get("public_check") or {}
            maj = (g.get("public_majority") or {}).get("team")
            if chk.get("money") != "with public" or not maj:
                continue                      # not a game the rule considers
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            sit = g.get("situational") or {}
            sh, sa = sit.get("home") or {}, sit.get("away") or {}
            if (not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int)
                    or not all(isinstance(x.get(k), int) for x in (sh, sa)
                               for k in ("wins", "losses"))):
                continue
            away, home = m.split(" @ ")
            if adv not in (away, home) or maj not in (away, home):
                continue
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            def wp(s):
                t = s["wins"] + s["losses"]
                return s["wins"] / t if t else 0.5
            rec = {home: wp(sh), away: wp(sa)}
            other = home if maj == away else away
            tot = _implied(a_ml) + _implied(o_ml)
            if maj not in price or tot <= 0:
                continue
            rows.append({
                "date": date, "side": maj, "odds": price[maj],
                "won": res["winner"] == maj,
                "p": _implied(price[maj]) / tot,
                "gap": rec[maj] - rec[other],
            })
    return rows


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1
               for r in rs) / len(rs)


def _fmt(rs) -> str:
    if not rs:
        return "—"
    w = sum(1 for r in rs if r["won"])
    return f"{w}-{len(rs)-w} · **{_roi(rs):+.1%}** (n={len(rs)})"


def build() -> str:
    rows = collect()
    md = ["# Does \"better on record\" add anything to the rule?", "",
          "_Every game the consensus rule would have CONSIDERED — handle "
          "agreeing with tickets, majority readable — bet or not. Backing "
          "the consensus side. Nine times the sample of our own settled "
          "picks, and not selected on how our betting turned out._", "",
          f"- qualifying games: **{len(rows)}**", ""]
    if len(rows) < 300:
        return "\n".join(md + ["Not enough qualifying games.", ""])

    cells = []
    md += [f"- baseline, backing the consensus side in all of them: "
           f"{_fmt(rows)}", "",
           "## 1. By record gap", "", "| record gap | backing the consensus side |",
           "|---|---|"]
    bands = [(f"much better (> +{GAP_HI:.2f})", lambda r: r["gap"] > GAP_HI),
             ("close (-0.10 to +0.10)", lambda r: -GAP_HI <= r["gap"] <= GAP_HI),
             (f"much worse (< -{GAP_HI:.2f})", lambda r: r["gap"] < -GAP_HI)]
    for label, test in bands:
        sub = [r for r in rows if test(r)]
        cells.append((label, sub))
        md.append(f"| {label} | {_fmt(sub)} |")
    md.append("")

    # --- 2. the confound -------------------------------------------------
    md += ["## 2. Within price bands — is the gap just the price again?", "",
           "_r(gap, price) on our own picks was -0.61, so this is the test "
           "that matters._", "",
           "| price band | gap > +0.10 | gap ≤ +0.10 |", "|---|---|---|"]
    pb = [("≤ -150", lambda o: o <= -150),
          ("-149..-101", lambda o: -149 <= o <= -101),
          ("+100 and longer", lambda o: o >= 100)]
    for plabel, ptest in pb:
        sub = [r for r in rows if ptest(r["odds"])]
        hi = [r for r in sub if r["gap"] > GAP_HI]
        lo = [r for r in sub if r["gap"] <= GAP_HI]
        cells += [(f"{plabel} · gap hi", hi), (f"{plabel} · gap lo", lo)]
        md.append(f"| {plabel} | {_fmt(hi)} | {_fmt(lo)} |")
    md += ["", "_If the left column beats the right in EVERY band, the gap is "
           "carrying something the price is not. If it only wins where "
           "favourites live, it is the price._", ""]

    # --- 3. time holdout --------------------------------------------------
    hi_all = [r for r in rows if r["gap"] > GAP_HI]
    md += ["## 3. Does it hold in time?", "",
           "| period | gap > +0.10 |", "|---|---|",
           f"| before {HOLDOUT} | {_fmt([r for r in hi_all if r['date'] < HOLDOUT])} |",
           f"| {HOLDOUT} onward | {_fmt([r for r in hi_all if r['date'] >= HOLDOUT])} |",
           f"| since the rule went live ({RULE_LIVE}) | "
           f"{_fmt([r for r in hi_all if r['date'] >= RULE_LIVE])} |", ""]

    # --- 4. corrections ---------------------------------------------------
    pool = [(l, s) for l, s in cells if len(s) >= MIN_CELL]
    if pool:
        bl, bs = max(pool, key=lambda c: _roi(c[1]))
        obs = _roi(bs) * 100
        plan = [[(grade.american_profit(r["odds"]), r["p"]) for r in s]
                for _, s in pool]
        rng = random.Random(17)
        null = [max(sum(w if rng.random() < p else -1 for w, p in pl) / len(pl)
                    for pl in plan) * 100 for _ in range(TRIALS)]
        pv = (sum(1 for x in null if x >= obs) + 1) / (len(null) + 1)
        md += ["## 4. Paying for the look", "",
               f"- cells at n≥{MIN_CELL}: **{len(pool)}**",
               f"- best: **{bl}** at {obs:+.1f}%",
               f"- biggest a price-redraw manufactures: median "
               f"**{st.median(null):+.1f}%**, 95th "
               f"**{sorted(null)[int(.95*len(null))]:+.1f}%**",
               f"- **corrected p = {pv:.3f}**", "",
               ("**Clears.**" if pv < 0.05 else "**Does not clear.**"), ""]

        rh = random.Random(4)
        tag = [rh.random() < 0.5 for _ in hi_all]
        a = [r for r, t in zip(hi_all, tag) if t]
        b = [r for r, t in zip(hi_all, tag) if not t]
        if min(len(a), len(b)) >= MIN_HALF:
            md += [f"- split-half of **gap > +0.10**: {_fmt(a)} against "
                   f"{_fmt(b)}", ""]

    md += ["## What would follow", "",
           "- surviving all four would make this a candidate SEVENTH gate: "
           "require the consensus side to be better on record before backing "
           "it. It would cut volume, and the cut has to be measured before "
           "anything ships",
           "- failing any one of them means the price control passing twice "
           "on 18 and 21 games was luck, and this joins the other thirty-odd",
           "- nothing changes on the board from this file.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "quality_gate.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
