"""
Point-in-time backtest: reconstruct what the edge finder WOULD have picked on
each of the last N days, and settle those picks against actual results at $1/pick.

Honest limits (see README):
  - Past public sentiment uses FORUM history only - covers serves no historical
    consensus %, so these picks run on the weaker forum signal (the live system
    prefers consensus when available).
  - Stats are point-in-time last-5 (no lookahead), but the SOS opponent-quality
    term still uses current-season wOBA/FIP totals (small forward bias).
  - Settlement is even money (+100): no true historical closing odds exist.

Runs on GitHub Actions (the APIs are firewalled in the build sandbox).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import covers, grade, mlb_api
from .analysis import evaluate_game

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("backtest")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")


def date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def run(end: str, days: int) -> dict:
    dates = date_range(end, days)
    log.info("Backtesting %s .. %s (%d days)", dates[0], dates[-1], days)

    # Pull every day's schedule once; collect the union of teams for the forum.
    schedules: dict[str, list] = {}
    teams: dict[str, str] = {}
    for d in dates:
        try:
            games = mlb_api.schedule_for(d)
        except Exception as exc:
            log.warning("schedule %s failed: %s", d, exc)
            games = []
        schedules[d] = games
        for g in games:
            for t in (g.home, g.away):
                teams[t.name] = t.abbreviation
    log.info("Found %d games across %d teams", sum(len(v) for v in schedules.values()), len(teams))

    try:
        forum_hist = covers.forum_day_counts(list(teams.items()), dates)
    except Exception as exc:
        log.warning("forum history failed: %s", exc)
        forum_hist = {d: {} for d in dates}

    entries: list[dict] = []
    bankroll = 0.0
    wins = losses = unsettled = 0

    for d in dates:
        try:
            results = mlb_api.results_for(d)
        except Exception as exc:
            log.warning("results %s failed: %s", d, exc)
            results = {}
        fcounts = forum_hist.get(d, {})

        for g in schedules[d]:
            try:
                mlb_api.enrich_with_stats(g, d, as_of=d)  # point-in-time
            except Exception as exc:
                log.warning("enrich %s failed: %s", g.game_pk, exc)
                continue
            r = evaluate_game(g, {}, fcounts)  # consensus={} -> forum-only public
            if not r["flagged"]:
                continue
            res = results.get(g.game_pk)
            if not res or not res["final"] or not res["winner"]:
                unsettled += 1
                continue
            won = res["winner"] == r["pick"]
            profit = grade.american_profit(grade.ODDS) if won else -grade.STAKE
            bankroll = round(bankroll + profit, 2)
            wins += int(won)
            losses += int(not won)
            entries.append({
                "date": d, "matchup": r["matchup"], "pick": r["pick"],
                "result": "W" if won else "L",
                "score": f"{res['away']} {res['away_score']} @ {res['home']} {res['home_score']}",
                "profit": round(profit, 2), "bankroll_after": bankroll,
            })

    return {
        "start": dates[0], "end": dates[-1], "days": days,
        "stake": grade.STAKE, "odds_assumption": f"+{grade.ODDS} (even money)",
        "public_signal": "forum history only (no historical consensus)",
        "record": {"wins": wins, "losses": losses, "picks": wins + losses},
        "profit_units": bankroll,
        "unsettled_picks": unsettled,
        "entries": entries,
    }


def summary_md(rep: dict) -> str:
    r = rep["record"]
    out = [f"# Backtest {rep['start']} → {rep['end']} ({rep['days']} days)", ""]
    out.append(f"**Profit: {rep['profit_units']:+.2f} units** "
               f"({r['wins']}-{r['losses']} on {r['picks']} picks, $1/pick at even money)")
    out.append(f"_Public signal: {rep['public_signal']}; stats point-in-time; "
               f"even-money settlement._")
    out.append("")
    if not rep["entries"]:
        out.append("No settleable picks in the window "
                   "(forum signal may be thin, or no public-vs-stats edges met the win condition).")
    else:
        out.append("| Date | Pick | Result | Score | Bankroll |")
        out.append("|---|---|---|---|---|")
        for e in rep["entries"]:
            out.append(f"| {e['date']} | {e['pick']} | {e['result']} | {e['score']} "
                       f"| {e['bankroll_after']:+.2f} |")
    if rep["unsettled_picks"]:
        out.append(f"\n_({rep['unsettled_picks']} flagged pick(s) couldn't be settled "
                   f"and are excluded.)_")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Point-in-time backtest of the edge finder")
    parser.add_argument("--days", type=int, default=10)
    parser.add_argument("--end", default=yesterday_eastern(),
                        help="last date to backtest (YYYY-MM-DD); default = yesterday US/Eastern")
    args = parser.parse_args()

    rep = run(args.end, args.days)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / f"backtest_{rep['start']}_{rep['end']}.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "latest_backtest.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
