"""
Win-condition calibration: does each win-condition signal actually predict winning?

For every completed game in a window, reconstruct each team's win condition
point-in-time (their last-5 going in) and check whether they won that game. Then,
for each of the five back-test counts, compare the win rate when a team scored
high on it vs. low - the "lift" over the ~50% base rate. That tells us, with data,
which conditions are worth trusting and how to weight them.

Uses only cheap, cached team-level data (team game logs + season FIP via
strength), so it can span the whole season. The FIP that sets the bars is the
team's season FIP here (a stand-in for the live starter+bullpen FIP) - a small,
documented approximation, same spirit as the existing backtest.

Runs on GitHub Actions (the MLB API is firewalled in the build sandbox).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import mlb_api, strength
from .analysis import _rpg, win_condition_core

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("wc_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
CONDITIONS = ["scored_target", "held_under_ceiling", "complete_win_condition",
              "actually_won", "out_hit"]


def _date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _team_wc(team_id: int, opp_id: int, season: int, as_of: str) -> dict | None:
    last5 = mlb_api.team_last5_gamelog(team_id, season, as_of=as_of)
    opp5 = mlb_api.team_last5_gamelog(opp_id, season, as_of=as_of)
    if not last5 or not opp5:
        return None
    team_fip = strength.team_strength(team_id, season, as_of=as_of)["fip"]
    opp_fip = strength.team_strength(opp_id, season, as_of=as_of)["fip"]
    return win_condition_core(last5, team_fip, _rpg(opp5), opp_fip)


def collect(end: str, days: int) -> list[dict]:
    """One row per team-game: each condition's count (0-5) and whether they won."""
    rows: list[dict] = []
    for d in _date_range(end, days):
        season = int(d[:4])
        try:
            games = mlb_api.schedule_for(d)
            results = mlb_api.results_for(d)
        except Exception as exc:
            log.warning("fetch %s failed: %s", d, exc)
            continue
        for g in games:
            res = results.get(g.game_pk)
            if not res or not res["final"] or not res["winner"]:
                continue
            for team, opp in ((g.home, g.away), (g.away, g.home)):
                wc = _team_wc(team.team_id, opp.team_id, season, d)
                if not wc:
                    continue
                row = {c: wc["back_test"][c] for c in CONDITIONS}
                row["won"] = int(res["winner"] == team.name)
                rows.append(row)
        log.info("collected through %s (%d team-games)", d, len(rows))
    return rows


def analyze(rows: list[dict]) -> dict:
    n = len(rows)
    base = sum(r["won"] for r in rows) / n if n else 0.0
    out = {"team_games": n, "base_win_rate": round(base, 3), "conditions": {}}
    for c in CONDITIONS:
        by_count = {}
        for k in range(6):
            grp = [r for r in rows if r[c] == k]
            if grp:
                by_count[k] = {"n": len(grp), "win_rate": round(sum(r["won"] for r in grp) / len(grp), 3)}
        hi = [r for r in rows if r[c] >= 3]          # "met it consistently" (3+/5)
        lo = [r for r in rows if r[c] < 3]
        hr = sum(r["won"] for r in hi) / len(hi) if hi else None
        lr = sum(r["won"] for r in lo) / len(lo) if lo else None
        out["conditions"][c] = {
            "win_rate_when_high_3plus": round(hr, 3) if hr is not None else None,
            "win_rate_when_low_under3": round(lr, 3) if lr is not None else None,
            "lift": round(hr - lr, 3) if hr is not None and lr is not None else None,
            "by_count": by_count,
        }
    return out


def summary_md(rep: dict) -> str:
    out = [f"# Win-condition calibration — {rep['window']}", ""]
    out.append(f"**{rep['analysis']['team_games']} team-games** · base win rate "
               f"{rep['analysis']['base_win_rate']:.0%}")
    out.append("")
    out.append("Win rate when a team hit each condition **3+/5** vs **<3/5**, and the lift:")
    out.append("")
    out.append("| Condition | hit 3+/5 | hit <3/5 | lift |")
    out.append("|---|---|---|---|")
    items = sorted(rep["analysis"]["conditions"].items(),
                   key=lambda kv: kv[1]["lift"] if kv[1]["lift"] is not None else -9)
    for c, v in reversed(items):
        hi = f"{v['win_rate_when_high_3plus']:.0%}" if v["win_rate_when_high_3plus"] is not None else "—"
        lo = f"{v['win_rate_when_low_under3']:.0%}" if v["win_rate_when_low_under3"] is not None else "—"
        lift = f"{v['lift']:+.0%}" if v["lift"] is not None else "—"
        out.append(f"| {c} | {hi} | {lo} | **{lift}** |")
    out.append("")
    out.append("_Higher lift = the condition separates winners from losers more. "
               "A lift near 0 means it doesn't predict winning. Season FIP stands in "
               "for the live starter+bullpen FIP that sets the bars._")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Calibrate the win condition against actual results")
    p.add_argument("--days", type=int, default=21)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()

    rows = collect(args.end, args.days)
    rep = {"window": f"{_date_range(args.end, args.days)[0]} → {args.end} ({args.days} days)",
           "analysis": analyze(rows)}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "wc_calibration.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "wc_calibration.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
