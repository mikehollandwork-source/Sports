"""
Window experiment: would rating teams on the last 10 (or 15, or 20) games instead
of the last 5 have produced a positive-ROI model?

This tests the ROOT CAUSE the pressure test pointed at. Every gate we tried died
out-of-sample, and the suspicion is the inputs: a 5-game window is ~20 plate
appearances per hitter, which is mostly variance. If that's right, widening the
window should measurably sharpen the model. If a 10/15/20-game window separates
winners from losers no better than 5, the problem isn't the window - it's the
approach.

Method (point-in-time, no leakage):
  * for each historical slate, rebuild the games and re-enrich them with as_of=date
    so only games BEFORE that date are visible - exactly what we'd have known
  * recompute the statistical favorite + margin for each window n
  * price each side from the FROZEN snapshot (the real pre-game moneylines)
  * grade vs the actual winner

The headline metric is CALIBRATION SPREAD (win% at high margin minus win% at low
margin), not ROI - it measures model quality directly and needs far less data to
be meaningful. ROI is reported alongside.

The full-season game log is cached per player, so the 2nd..4th windows are nearly
free; the first window pays the API cost. Runs on GitHub Actions.
Writes output/window_test.md.
"""

from __future__ import annotations

import glob
import json
import logging
from pathlib import Path

from . import grade, mlb_api
from .analysis import HOME_FIELD, platoon_factor, statistical_favorite, win_condition

log = logging.getLogger("window_test")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
HOLDOUT_FROM = "2026-07-23"
WINDOWS = (5, 10, 15, 20)


def _prices(g: dict) -> dict:
    """{team_name: pre-game moneyline} from a frozen snapshot game."""
    pc = g.get("pick_criteria") or {}
    adv, mla, mlo = pc.get("advantage_team"), pc.get("advantage_moneyline"), \
        pc.get("opponent_moneyline")
    if not adv or " @ " not in g.get("matchup", ""):
        return {}
    away, home = g["matchup"].split(" @ ")
    opp = home if adv == away else away
    out = {}
    if mla is not None:
        out[adv] = int(mla)
    if mlo is not None:
        out[opp] = int(mlo)
    return out


def _margin_for(game, n: int):
    """(advantage_team_name, margin) recomputed at window n, or None."""
    try:
        home_opp = game.away.probable_pitcher.hand if game.away.probable_pitcher else ""
        away_opp = game.home.probable_pitcher.hand if game.home.probable_pitcher else ""
        game.home.platoon_factor = platoon_factor(game.home.offense.get("bats", []), home_opp)
        game.away.platoon_factor = platoon_factor(game.away.offense.get("bats", []), away_opp)
        wc_h, wc_a = win_condition(game.home, game.away), win_condition(game.away, game.home)
        cons = ((wc_h["back_test"]["out_hit"], wc_a["back_test"]["out_hit"])
                if wc_h and wc_a else None)
        adv, hs, as_ = statistical_favorite(game, cons)
        return adv.name, abs(hs - as_)
    except Exception as exc:
        log.warning("margin failed (n=%s): %s", n, exc)
        return None


def collect() -> dict:
    """{window: [rec]} - one rec per game per window."""
    out = {n: [] for n in WINDOWS}
    files = sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json")))
    for f in files:
        date = Path(f).stem.split("picks_")[1]
        day = json.loads(Path(f).read_text())
        snap = {g.get("game_pk"): g for g in day.get("games", [])}
        try:
            results = mlb_api.results_for(date)
            games = mlb_api.schedule_for(date)
        except Exception as exc:
            log.warning("slate %s unavailable: %s", date, exc)
            continue
        for gm in games:
            res = results.get(gm.game_pk)
            sg = snap.get(gm.game_pk)
            if not res or not res.get("final") or not res.get("winner") or not sg:
                continue
            prices = _prices(sg)
            if not prices:
                continue
            for n in WINDOWS:
                try:
                    mlb_api.enrich_with_stats(gm, date, as_of=date, n=n)
                except Exception as exc:
                    log.warning("enrich failed %s n=%s: %s", gm.game_pk, n, exc)
                    continue
                mr = _margin_for(gm, n)
                if not mr:
                    continue
                adv, margin = mr
                ml = prices.get(adv)
                if ml is None:
                    continue
                out[n].append({"date": date, "adv": adv, "margin": margin,
                               "ml": ml, "won": res["winner"] == adv,
                               "holdout": date >= HOLDOUT_FROM})
        log.info("slate %s done", date)
    return out


def _roi(rows):
    if not rows:
        return None
    w = sum(1 for r in rows if r["won"])
    u = sum(grade.american_profit(r["ml"]) if r["won"] else -1 for r in rows)
    return w, len(rows) - w, round(u, 2), u / len(rows)


def _cell(rows):
    r = _roi(rows)
    if not r:
        return "—"
    w, l, u, roi = r
    return f"{w}-{l} ({w/(w+l):.0%}) · {roi:+.1%} (n={w+l})"


def build() -> str:
    data = collect()
    md = ["# Window experiment — does a longer form sample fix the model?", "",
          "_Teams re-rated on the last **n** games instead of 5, point-in-time "
          "(as_of), priced at the real frozen moneylines. **Calibration spread** = "
          "win% at margin ≥0.5 minus win% at margin <0.5; it measures model quality "
          "directly and is the number that matters. A longer window helps only if "
          "that spread WIDENS._", ""]

    md += ["## Calibration spread by window (the headline)", "",
           "| window | high-margin (≥0.5) | low-margin (<0.5) | **spread** | n |",
           "|---|---|---|---|---|"]
    for n in WINDOWS:
        rows = data.get(n) or []
        if not rows:
            md.append(f"| last {n} | — | — | — | 0 |")
            continue
        hi = [r for r in rows if r["margin"] >= 0.5]
        lo = [r for r in rows if r["margin"] < 0.5]
        if not hi or not lo:
            md.append(f"| last {n} | — | — | — | {len(rows)} |")
            continue
        hw = sum(1 for r in hi if r["won"]) / len(hi)
        lw = sum(1 for r in lo if r["won"]) / len(lo)
        md.append(f"| last {n} | {hw:.1%} (n={len(hi)}) | {lw:.1%} (n={len(lo)}) | "
                  f"**{(hw-lw)*100:+.1f} pts** | {len(rows)} |")
    md.append("")

    md += ["## ROI by window (bet the stat side, ungated)", "",
           "| window | ALL | in-sample | HOLDOUT |", "|---|---|---|---|"]
    for n in WINDOWS:
        rows = data.get(n) or []
        ins = [r for r in rows if not r["holdout"]]
        hold = [r for r in rows if r["holdout"]]
        md.append(f"| last {n} | {_cell(rows)} | {_cell(ins)} | {_cell(hold)} |")
    md.append("")

    md += ["## ROI by window, high-margin picks only (margin ≥0.5)", "",
           "| window | ALL | in-sample | HOLDOUT |", "|---|---|---|---|"]
    for n in WINDOWS:
        rows = [r for r in (data.get(n) or []) if r["margin"] >= 0.5]
        ins = [r for r in rows if not r["holdout"]]
        hold = [r for r in rows if r["holdout"]]
        md.append(f"| last {n} | {_cell(rows)} | {_cell(ins)} | {_cell(hold)} |")
    md.append("")

    # how often do the windows even disagree about which side is better?
    base = {(r["date"], r["adv"]) for r in (data.get(5) or [])}
    for n in WINDOWS[1:]:
        same = sum(1 for r in (data.get(n) or []) if (r["date"], r["adv"]) in base)
        tot = len(data.get(n) or [])
        if tot:
            md.append(f"_last {n} picks the same side as last 5 on {same}/{tot} "
                      f"games ({same/tot:.0%})._")
    md.append("")
    md.append("_Point-in-time: only games before each slate date are visible at any "
              "window. If the spread does not widen with n, the window is not the "
              "bottleneck._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "window_test.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
