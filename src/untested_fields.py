"""
The board fields no analysis has ever read — alone and in combination.

HOW THESE WERE FOUND
Every key on a board game was cross-referenced against every analysis module.
Ten were referenced by none of them. Two are substantive:

  pm_quote   {pm_pct, pm_american, edge_pts, vs_book} on 78% of games -
             POLYMARKET'S price against the book's, with the gap already
             quantified in points. A second real-money market disagreeing
             with the sportsbook is the most promising untested thing here,
             because it is not our model - it is someone else's money.

  projected  {win_prob, fair_american} on 73% - the board's OWN fair price,
             which has never been compared to the price actually offered.
             Expect little: `divergence` already showed the stat model's
             deviation from the market is anti-informative, and this is that
             deviation stated in odds. Included because "expect little" is
             not a measurement.

And the rest: line_vs_money (64%), starred (77%), public_edge (99%),
public_trusted (97%), public_pct_against (27%).

  stay_bet / stay_odds are populated on 0 of 1,271 rows. They are dead
  fields, reported here so the loose end is closed rather than carried.

WHY COMBINATIONS ARE TESTED THE WAY THEY ARE
Six live fields means 57 non-empty subsets, and a subset scan on this data
has already produced a +10.5% "best" against a noise median of +19.0%
(`stat_subsets`). So every subset enters one grid, the best is corrected by a
max-statistic permutation with outcomes redrawn from de-vigged prices, and
whatever survives is split-halved. A cell that clears one and not the other
is not a finding.

Writes output/untested_fields.md.
"""

from __future__ import annotations

import glob
import itertools
import json
import logging
import random
import statistics as st
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("untested_fields")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 3000
MIN_CELL = 40
MIN_HALF = 15


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
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue
            pmq = pc.get("pm_quote") or {}
            proj = pc.get("projected") or {}
            fair = proj.get("fair_american")
            # model edge: how much longer the book pays than the model's fair
            model_edge = None
            if isinstance(fair, int):
                model_edge = (_implied(fair) - _implied(a_ml)) * 100
            rows.append({
                "date": date, "adv_odds": a_ml, "opp_odds": o_ml,
                "adv_won": res["winner"] == adv,
                "p_adv": _implied(a_ml) / tot,
                "pm_edge": pmq.get("edge_pts"),
                "pm_better": (pmq.get("vs_book") == "better") if pmq else None,
                "model_edge": model_edge,
                "lvm": pc.get("line_vs_money"),
                "starred": len(pc.get("starred") or []) if pc.get("starred") is not None else None,
                "pub_edge": pc.get("public_edge"),
                "pub_trusted": pc.get("public_trusted"),
                "pub_against": pc.get("public_pct_against"),
            })
    return rows


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["adv_odds"]) if r["adv_won"] else -1
               for r in rs) / len(rs)


def _fmt(rs) -> str:
    if not rs:
        return "—"
    w = sum(1 for r in rs if r["adv_won"])
    return f"{w}-{len(rs)-w} · **{_roi(rs):+.1%}** (n={len(rs)})"


# each condition selects games where the field points AT the advantage side
CONDS = {
    "PM says better than book": lambda r: r["pm_better"] is True,
    "PM edge ≥ 2 pts": lambda r: isinstance(r["pm_edge"], (int, float)) and r["pm_edge"] >= 2,
    "model fair beats price": lambda r: isinstance(r["model_edge"], (int, float)) and r["model_edge"] > 0,
    "line vs money 'against'": lambda r: r["lvm"] == "against",
    "starred (any tag)": lambda r: isinstance(r["starred"], int) and r["starred"] > 0,
    "public edge true": lambda r: r["pub_edge"] is True,
    "public trusted": lambda r: r["pub_trusted"] is True,
}


def build() -> str:
    rows = collect()
    md = ["# The board fields nothing has ever read", "",
          "_Every key on a board game cross-referenced against every analysis "
          "module; ten were referenced by none. Backing the ADVANTAGE side "
          "when each field points at it._", "",
          f"- graded games: **{len(rows)}**", "",
          "_`stay_bet` and `stay_odds` are populated on 0 of 1,271 rows — "
          "dead fields, noted so the loose end is closed rather than "
          "carried._", "",
          f"- baseline, backing the advantage side in every game: "
          f"{_fmt(rows)}", ""]
    if len(rows) < 300:
        return "\n".join(md + ["Not enough graded games.", ""])

    md += ["## Each field alone", "", "| condition | backing the advantage side |",
           "|---|---|"]
    cells = []
    for label, fn in CONDS.items():
        sub = [r for r in rows if fn(r)]
        cells.append((label, sub))
        md.append(f"| {label} | {_fmt(sub)} |")
    md.append("")

    # --- combinations -----------------------------------------------------
    md += ["## In combination", "",
           "_Every non-empty subset of the seven, kept when it still has "
           f"n≥{MIN_CELL}. Sorted best first; the correction below is what "
           "decides whether the top of this list means anything._", "",
           "| combination | backing the advantage side |", "|---|---|"]
    names = list(CONDS)
    combos = []
    for k in range(2, len(names) + 1):
        for cmb in itertools.combinations(names, k):
            sub = [r for r in rows if all(CONDS[c](r) for c in cmb)]
            if len(sub) >= MIN_CELL:
                combos.append((" + ".join(cmb), sub))
    combos.sort(key=lambda c: -_roi(c[1]))
    for label, sub in combos[:12]:
        md.append(f"| {label} | {_fmt(sub)} |")
    if not combos:
        md.append(f"| _no combination reaches n={MIN_CELL}_ | — |")
    md += ["", f"_combinations reaching n≥{MIN_CELL}: **{len(combos)}**_", ""]

    # --- pay for the scan --------------------------------------------------
    pool = [(l, s) for l, s in (cells + combos) if len(s) >= MIN_CELL]
    if not pool:
        return "\n".join(md + ["No cell is large enough to test.", ""])
    bl, bs = max(pool, key=lambda c: _roi(c[1]))
    obs = _roi(bs) * 100
    plan = [[(grade.american_profit(r["adv_odds"]), r["p_adv"]) for r in s]
            for _, s in pool]
    rng = random.Random(64)
    null = [max(sum(w if rng.random() < p else -1 for w, p in pl) / len(pl)
                for pl in plan) * 100 for _ in range(TRIALS)]
    pv = (sum(1 for x in null if x >= obs) + 1) / (len(null) + 1)
    md += ["## Does the best of them beat the search?", "",
           f"- cells at n≥{MIN_CELL}: **{len(pool)}**",
           f"- best: **{bl}** at {obs:+.1f}%",
           f"- biggest a price-redraw manufactures: median "
           f"**{st.median(null):+.1f}%**, 95th pct "
           f"**{sorted(null)[int(.95*len(null))]:+.1f}%**",
           f"- **corrected p = {pv:.3f}**", "",
           ("**Clears the scan.**" if pv < 0.05 else
            "**Does not clear.** A scan this wide manufactures a cell this "
            "good often enough that the number is the width of the search."),
           ""]

    rh = random.Random(88)
    tag = [rh.random() < 0.5 for _ in bs]
    a = [r for r, t in zip(bs, tag) if t]
    b = [r for r, t in zip(bs, tag) if not t]
    if min(len(a), len(b)) >= MIN_HALF:
        md += [f"- split-half of **{bl}**: {_fmt(a)} against {_fmt(b)}", "",
               "_Two halves of the same cell landing far apart means noise, "
               "whatever the pooled number says._", ""]

    md += ["## How to read this", "",
           "- `pm_quote` was the one worth hoping for: a second real-money "
           "market disagreeing with the sportsbook is not our model talking",
           "- `projected` restates the stat model's deviation from the market "
           "in odds, and `divergence` already found that deviation "
           "anti-informative, so a poor showing there confirms rather than "
           "surprises",
           "- nothing here changes the board.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "untested_fields.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
