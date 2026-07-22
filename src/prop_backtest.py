"""
Prop backtest: does the hits-in-wins 1+HIT prop, combined with our ML signals,
actually make ROI?

The prop is fully reconstructable for past games - the season-wins set, that
day's lineup, and each hitter's game log are all historical MLB API calls - so
for every historical BOARD play we rebuild the prop we WOULD have chosen
(props.best_hit_prop, with the game itself excluded from the wins sample so the
pick is honestly pre-game), then grade whether the chosen hitter recorded a hit
and whether the ML+prop parlay cashed. Results are split by which signal the
underlying pick carried, so you can read "prop + margin", "prop + line", etc.

Pricing: singles at the assumed 1+hit line (PROP_PRICE - real historical prop
lines aren't captured); parlays combine the REAL frozen ML with that assumed
prop price. So win% is real; the ROI columns are assumed-price estimates and
labeled as such.

Runs on GitHub Actions (the MLB API is firewalled in the dev sandbox). Writes
output/prop_backtest.md.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

from . import grade, mlb_api, props
from .prop_grade import PROP_PRICE, parlay_odds
from .signal_backtest import signals, SIGNALS

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
BOARD_PLAYS = ("pick", "lock", "lean")   # historical board tiers (lock/lean retired)


def _units(rows: list[dict]) -> tuple[int, int, float]:
    """(wins, losses, units) at each row's odds, $1/bet."""
    w = sum(1 for r in rows if r["won"])
    u = sum(grade.american_profit(r["odds"]) if r["won"] else -1 for r in rows)
    return w, len(rows) - w, round(u, 2)


def _roi(label: str, rows: list[dict]) -> str:
    if not rows:
        return f"| {label} | 0 | — | — |"
    w, l, u = _units(rows)
    return f"| {label} (n={len(rows)}) | {w}-{l} ({w / len(rows):.0%}) | {u:+.2f}u | {u / len(rows):+.1%} |"


def build() -> str:
    plays: list[dict] = []
    scanned = reconstructed = 0
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        day = json.loads(Path(f).read_text())
        try:
            results = mlb_api.results_for(date)
            sched = {g.game_pk: g for g in mlb_api.schedule_for(date)}
        except Exception:
            continue
        for g in day.get("games", []):
            pc = g.get("pick_criteria") or {}
            if pc.get("play") not in BOARD_PLAYS:
                continue
            scanned += 1
            pk = g.get("game_pk")
            res = results.get(pk)
            sig = signals(g)
            gm = sched.get(pk)
            if not res or not res.get("final") or not res.get("winner") or not sig or not gm:
                continue
            adv = sig["_adv"]
            is_home = adv == gm.home.name
            team = gm.home if is_home else gm.away
            try:
                prop = props.best_hit_prop(pk, team.team_id, date, is_home, exclude_pk=pk)
            except Exception:
                prop = None
            if not prop:
                continue
            hits = mlb_api.player_hits(pk, prop["player_id"])
            if hits is None:
                continue
            reconstructed += 1
            got_hit = hits >= 1
            team_won = res["winner"] == adv
            ml = sig["_ml"]
            plays.append({
                "sig": sig, "got_hit": got_hit, "team_won": team_won,
                "hit_rate": prop["hit_rate"], "ml": ml,
                # single: prop alone at the assumed price
                "single": {"won": got_hit, "odds": PROP_PRICE},
                # parlay: team ML + prop (needs a real ML); wins only if both hit
                "parlay": ({"won": team_won and got_hit, "odds": parlay_odds(int(ml), PROP_PRICE)}
                           if ml is not None else None),
            })

    md = [f"# Prop backtest — {reconstructed} props reconstructed "
          f"of {scanned} historical board plays", "",
          "_The hits-in-wins prop rebuilt pre-game for each past board pick "
          "(target game excluded from the wins sample). Win% is real; ROI uses "
          f"the assumed {PROP_PRICE:+d} 1+hit line (real historical prop lines "
          "aren't captured), so read ROI as an estimate._", ""]

    singles = [p["single"] for p in plays]
    parlays = [p["parlay"] for p in plays if p["parlay"]]
    md += ["## Overall — every board play's prop", "",
           "| bet | record | units | ROI/bet |", "|---|---|---|---|",
           _roi("prop SINGLE (player 1+ hit)", singles),
           _roi("prop PARLAY (team ML + 1+ hit)", parlays), ""]

    # The core question: prop filtered by each of our ML signals. A play counts
    # for a signal when that signal fired on the underlying pick.
    md += ["## Prop + each signal (does a signal-filtered prop make ROI?)", "",
           "_Singles and ML+prop parlays, keeping only board plays where that "
           "signal fired on the moneyline pick._", "",
           "| signal on the pick | SINGLE record | S ROI | PARLAY record | P ROI |",
           "|---|---|---|---|---|"]
    for s in SIGNALS:
        sub = [p for p in plays if p["sig"].get(s) is True]
        ss = [p["single"] for p in sub]
        pp = [p["parlay"] for p in sub if p["parlay"]]
        if not ss:
            md.append(f"| {s} | 0 | — | 0 | — |")
            continue
        sw, sl, su = _units(ss)
        prow = f"{len(pp)} plays" if pp else "—"
        if pp:
            pw, pl, pu = _units(pp)
            prow = f"{pw}-{pl} ({pw / len(pp):.0%})"
            proi = f"{pu / len(pp):+.1%}"
        else:
            proi = "—"
        md.append(f"| {s} (n={len(ss)}) | {sw}-{sl} ({sw / len(ss):.0%}) "
                  f"| {su / len(ss):+.1%} | {prow} | {proi} |")
    md.append("")

    # Does the metric's own confidence carry? Split by the chosen hitter's
    # hits-in-wins rate - if higher-rate props hit more / earn more, the metric
    # is doing real work; if flat, it's just picking a warm bat.
    md += ["## By the prop's own hit-in-wins rate (is the metric predictive?)", "",
           "| chosen hitter's win hit-rate | SINGLE record | ROI/bet |", "|---|---|---|"]
    for lo, hi, lab in ((0, 70, "< 70%"), (70, 75, "70–74%"), (75, 80, "75–79%"),
                        (80, 200, "≥ 80%")):
        ss = [p["single"] for p in plays if lo <= p["hit_rate"] < hi]
        md.append(_roi(lab, ss))
    md.append("")

    md.append("_Point-in-time: prop chosen from the frozen board's advantage side "
              "with the graded game excluded from its wins sample; hit confirmed "
              "from the box score; $1/bet. ROI at the assumed prop price._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "prop_backtest.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
