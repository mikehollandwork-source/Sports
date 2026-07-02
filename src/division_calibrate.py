"""
Division analysis: does a team's form vs the opponent's division predict the game,
beyond its overall quality?

For each team-game we compute the team's run-diff/game vs the opponent's division
minus its overall run-diff/game (the "division delta", point-in-time) - positive
means it over-performs vs that division, negative means it struggles there. Then we
check whether that delta predicts winning. If it doesn't, "vs-division" splits are
noise (like the home/road split) and we don't add them.

Only counts a team-game once the team has a few games vs that division (MIN_GAMES).
Cheap (game logs + results). Runs on Actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import mlb_api

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("division_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
MIN_GAMES = 4     # need this many games vs the division for the delta to mean anything
DELTA = 0.5       # run-diff/game over/under-performance that counts as "clear"


def _date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def collect(end: str, days: int) -> list[dict]:
    """One row per team-game with enough vs-division history: {delta, won}."""
    rows: list[dict] = []
    for d in _date_range(end, days):
        season = int(d[:4])
        try:
            games = mlb_api.schedule_for(d)
            results = mlb_api.results_for(d)
            divs = mlb_api.team_divisions(season)
        except Exception as exc:
            log.warning("fetch %s failed: %s", d, exc)
            continue
        for g in games:
            res = results.get(g.game_pk)
            if not res or not res["final"] or not res["winner"]:
                continue
            for team, opp in ((g.home, g.away), (g.away, g.home)):
                opp_div = divs.get(opp.team_id)
                if not opp_div:
                    continue
                try:
                    f = mlb_api.team_division_form(team.team_id, season, opp_div, as_of=d)
                except Exception:
                    continue
                if f["vs_div_games"] < MIN_GAMES or f["delta"] is None:
                    continue
                rows.append({"delta": f["delta"], "won": int(res["winner"] == team.name)})
        log.info("collected through %s (%d team-games with vs-div history)", d, len(rows))
    return rows


def _wr(rows: list[dict]) -> tuple[int, float | None]:
    n = len(rows)
    return n, (round(sum(r["won"] for r in rows) / n, 3) if n else None)


def analyze(rows: list[dict]) -> dict:
    n, base = _wr(rows)
    over = [r for r in rows if r["delta"] >= DELTA]    # over-performs vs this division
    even = [r for r in rows if -DELTA < r["delta"] < DELTA]
    under = [r for r in rows if r["delta"] <= -DELTA]   # struggles vs this division
    _, orate = _wr(over)
    _, erate = _wr(even)
    _, urate = _wr(under)
    return {"team_games": n, "base_win_rate": base,
            "over_performs (>=+0.5 rd/g)": {"n": len(over), "win_rate": orate},
            "even": {"n": len(even), "win_rate": erate},
            "struggles (<=-0.5 rd/g)": {"n": len(under), "win_rate": urate},
            "lift": round(orate - urate, 3) if orate is not None and urate is not None else None}


def summary_md(rep: dict) -> str:
    a = rep["analysis"]
    out = [f"# Division analysis — {rep['window']}", ""]
    out.append(f"**{a['team_games']} team-games** (≥{MIN_GAMES} games vs the division) · "
               f"base win rate {a['base_win_rate']:.0%}" if a["base_win_rate"] is not None
               else "no qualifying team-games")
    out.append("")
    out.append("Win rate by how the team does vs the opponent's division "
               "(run-diff/g vs that division − its overall):")
    out.append("")
    out.append("| Division form | team-games | won |")
    out.append("|---|---|---|")
    for label in ("over_performs (>=+0.5 rd/g)", "even", "struggles (<=-0.5 rd/g)"):
        b = a[label]
        wr = f"{b['win_rate']:.0%}" if b["win_rate"] is not None else "—"
        out.append(f"| {label} | {b['n']} | {wr} |")
    out.append("")
    if a["lift"] is not None:
        out.append(f"**Lift:** over-performs vs struggles = **{a['lift']:+.0%}**")
    out.append("")
    out.append("_Delta isolates the division-specific effect from overall quality. "
               "Point-in-time, no lookahead._")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Division form analysis")
    p.add_argument("--days", type=int, default=95)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()

    rep = {"window": f"{_date_range(args.end, args.days)[0]} → {args.end} ({args.days} days)",
           "analysis": analyze(collect(args.end, args.days))}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "division_analysis.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "division_analysis.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
