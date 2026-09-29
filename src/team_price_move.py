"""
Team × price × line movement — and whether team identity survives the split.

WHAT WAS ASKED, AND THE PROBLEM WITH IT AS STATED
"Per-team line movement, and what price that team wins and loses at." Both
halves already exist and are null on their own: `team_line_move` put the
spread of team ROIs at p = 0.621 (no team-level signal at all, over 1,812
team-games) and its best of 113 cells at p = 0.078; `signal_by_price` put its
best of 75 price × signal cells at p = 0.581.

Crossing them multiplies the grid rather than the evidence: 30 teams × 5 price
bands × 2 directions is ~300 cells averaging six games apiece. A grid that
wide returns a +80% cell every time it is run, and the cell means nothing.
This file therefore reports that table as DECORATION and rests nothing on it.

THE LEAD THAT IS WORTH THE RUN
Inside `team_line_move` two sub-tests did clear, and only in one direction:

    against >= 0.5%   29 teams   spread 28.1%  vs 21.5% chance   p = 0.018
    against >= 1.0%   21 teams   spread 29.8%  vs 22.9% chance   p = 0.026

So when the line moves AGAINST a team, teams look less interchangeable than
chance allows - which would matter, because "line against" is the gate the
live rule is built on. Two caveats kept it from meaning anything yet: they are
2 of ~10 sub-tests, so ~0.18 after correction, and nobody has asked whether
the pattern repeats.

THE TESTS
  1. the spread test per price band - ONE number per band, not per cell, so
     it has power: do teams differ more than chance at this price?
  2. the same spread test inside "line against", corrected for how many
     sub-tests were run
  3. SPLIT-HALF on team ROIs within "line against": if team identity is real,
     the teams that did well in one half do well in the other. This is the
     test that has killed every candidate this season, and it is the one the
     original report never ran.

A spread that clears but does not repeat is thirty noisy numbers being wide,
which is what thirty noisy numbers do.

Writes output/team_price_move.md.
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

log = logging.getLogger("team_price_move")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 3000
MIN_TEAM = 12          # team-games needed before a team enters a spread test
MIN_HALF = 6

BANDS = [("≤-200", lambda o: o <= -200),
         ("-199..-140", lambda o: -199 <= o <= -140),
         ("-139..-110", lambda o: -139 <= o <= -110),
         ("-109..+109", lambda o: -109 <= o <= 109),
         ("+110..+159", lambda o: 110 <= o <= 159),
         ("≥+160", lambda o: o >= 160)]


def collect() -> list[dict]:
    """Two rows per game, one per team, the move signed toward that team."""
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
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            shift = (pc.get("line_check") or {}).get("implied_shift")
            if (not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int)
                    or not isinstance(shift, (int, float))):
                continue
            away, home = m.split(" @ ")
            if adv not in (away, home):
                continue
            opp = home if adv == away else away
            tot = _implied(a_ml) + _implied(o_ml)
            for team, odds, toward in ((adv, a_ml, shift), (opp, o_ml, -shift)):
                p = (_implied(odds) / tot) if tot > 0 else 0.5
                rows.append({"date": date, "team": team, "odds": odds,
                             "won": res["winner"] == team, "toward": toward,
                             "p": p})
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
    tail = "" if len(rs) >= 15 else "_"
    return f"{tail}{_roi(rs):+.0%} ({w}-{len(rs)-w}){tail}"


def _spread_test(rows, rng_seed: int) -> dict | None:
    """Do teams differ more than redrawn outcomes allow? One test, all the data."""
    by = defaultdict(list)
    for r in rows:
        by[r["team"]].append(r)
    live = {t: rs for t, rs in by.items() if len(rs) >= MIN_TEAM}
    if len(live) < 8:
        return None
    obs = st.pstdev([_roi(rs) for rs in live.values()]) * 100
    rng = random.Random(rng_seed)
    null = []
    for _ in range(TRIALS):
        sp = []
        for rs in live.values():
            u = sum(grade.american_profit(r["odds"]) if rng.random() < r["p"] else -1
                    for r in rs)
            sp.append(u / len(rs))
        null.append(st.pstdev(sp) * 100)
    p = (sum(1 for x in null if x >= obs) + 1) / (len(null) + 1)
    return {"teams": len(live), "obs": obs, "med": st.median(null),
            "p95": sorted(null)[int(.95 * len(null))], "p": p, "live": live}


def build() -> str:
    rows = collect()
    md = ["# Team, price and line movement", "",
          "_Two rows per game, one per team, the move signed toward that "
          "team._", "",
          f"- team-games: **{len(rows)}**", "",
          "## Why the full grid is decoration", "",
          "_30 teams × 6 price bands × 2 directions is ~360 cells. Both "
          "parent grids are already null on their own — team spread "
          "p = 0.621, price × signal best cell p = 0.581 — so crossing them "
          "multiplies the cells, not the evidence._", ""]
    if len(rows) < 500:
        return "\n".join(md + ["Not enough team-games.", ""])

    cell_n = []
    for _, test in BANDS:
        for direction in (1, -1):
            sub = [r for r in rows if test(r["odds"])
                   and (r["toward"] > 0) == (direction > 0)]
            by = defaultdict(int)
            for r in sub:
                by[r["team"]] += 1
            cell_n += list(by.values())
    md += [f"- cells in that grid: **{len(cell_n)}** · median games per cell: "
           f"**{st.median(cell_n) if cell_n else 0:.0f}**", "",
           "_A median cell of a handful of games returns a huge ROI by "
           "arithmetic, not by insight._", ""]

    # --- 1. spread test per price band ------------------------------------
    md += ["## 1. Do teams differ, at each price?", "",
           "_One test per band over all its games, rather than one per cell. "
           "If teams genuinely differ at a price, the SPREAD of their ROIs "
           "there beats what redrawn outcomes produce._", "",
           "| price band | teams | observed spread | chance | 95th | p |",
           "|---|---|---|---|---|---|"]
    for label, test in BANDS:
        sub = [r for r in rows if test(r["odds"])]
        res = _spread_test(sub, 11)
        if not res:
            md.append(f"| {label} | {len(set(r['team'] for r in sub))} | — | — "
                      f"| — | too few teams |")
            continue
        md.append(f"| {label} | {res['teams']} | {res['obs']:.1f}% | "
                  f"{res['med']:.1f}% | {res['p95']:.1f}% | **{res['p']:.3f}** |")
    md += ["", "_Six bands tested, so a single p just under 0.05 here is "
           "roughly 0.3 after correcting for having run six._", ""]

    # --- 2. the lead: line against -----------------------------------------
    against = [r for r in rows if r["toward"] <= -0.005]
    res = _spread_test(against, 23)
    md += ["## 2. The lead: teams inside \"line moved against\"", "",
           "_`team_line_move` found spread tests clearing here and only here "
           "(p = 0.018 at ≥0.5%, p = 0.026 at ≥1.0%), on 2 of ~10 sub-tests._",
           ""]
    if res:
        md += [f"- teams with ≥{MIN_TEAM} games: **{res['teams']}**",
               f"- observed spread **{res['obs']:.1f}%** against chance "
               f"**{res['med']:.1f}%** (95th {res['p95']:.1f}%)",
               f"- **p = {res['p']:.3f}** · after correcting for ~10 "
               f"sub-tests, roughly **{min(res['p'] * 10, 1.0):.2f}**", ""]

        # --- 3. split-half: does team identity REPEAT? ---------------------
        rh = random.Random(77)
        halves = ([], [])
        for r in against:
            halves[0 if rh.random() < 0.5 else 1].append(r)
        ha = defaultdict(list)
        hb = defaultdict(list)
        for r in halves[0]:
            ha[r["team"]].append(r)
        for r in halves[1]:
            hb[r["team"]].append(r)
        pairs = [(t, _roi(ha[t]) * 100, _roi(hb[t]) * 100) for t in res["live"]
                 if len(ha.get(t, [])) >= MIN_HALF and len(hb.get(t, [])) >= MIN_HALF]
        md += ["### Does a team's edge repeat across random halves?", ""]
        if len(pairs) >= 8:
            r_ = st.correlation([a for _, a, _ in pairs], [b for _, _, b in pairs])
            md += [f"- teams with ≥{MIN_HALF} games in BOTH halves: "
                   f"**{len(pairs)}**",
                   f"- **split-half r = {r_:+.2f}**", "",
                   ("_Positive: the teams that did well in one half did well "
                    "in the other, so team identity is carrying something "
                    "real inside line-against games._" if r_ > 0.3 else
                    "_Not repeatable. A team's line-against ROI in one half "
                    "does not predict the other, so the wide spread is thirty "
                    "noisy numbers being wide — which is what the spread test "
                    "cannot distinguish on its own._"), "",
                   "| team | half A | half B |", "|---|---|---|"]
            for t, a, b in sorted(pairs, key=lambda x: -x[1])[:10]:
                md.append(f"| {t} | {a:+.0f}% | {b:+.0f}% |")
            md.append("")
        else:
            md += [f"_Only {len(pairs)} teams have ≥{MIN_HALF} games in both "
                   "halves — too few to correlate._", ""]
    else:
        md += ["_Too few teams clear the minimum inside line-against._", ""]

    # --- the decorative table ---------------------------------------------
    md += ["## The full table (decoration — see above)", "",
           "| team | n | all | line toward | line against |", "|---|---|---|---|---|"]
    by = defaultdict(list)
    for r in rows:
        by[r["team"]].append(r)
    for team, rs in sorted(by.items(), key=lambda kv: -_roi(kv[1])):
        if len(rs) < MIN_TEAM:
            continue
        tw = [r for r in rs if r["toward"] > 0]
        ag = [r for r in rs if r["toward"] <= -0.005]
        md.append(f"| {team} | {len(rs)} | {_fmt(rs)} | {_fmt(tw)} | {_fmt(ag)} |")
    md += ["", "_Italic cells are under n=15. Nothing in this table is "
           "evidence; it is here to be read, not acted on._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "team_price_move.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
