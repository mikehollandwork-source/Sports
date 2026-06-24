"""
Grade the picks the edge finder made against actual MLB results and keep a
running $1-per-pick bankroll in output/ledger.json.

Each flagged pick is a $1 bet on that team's moneyline. We have no true
historical closing odds (covers serves only current lines), so settlement uses
an even-money (+100) assumption: a win is +$1.00, a loss is -$1.00. The ledger
is idempotent per date, so re-running a day never double-counts it.

Runs on GitHub Actions (the MLB API is firewalled in the build sandbox). Default
date is yesterday (US/Eastern) - i.e. grade the prior day once its games are final.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import zoneinfo
from pathlib import Path

from . import mlb_api

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("grade")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
LEDGER_PATH = OUTPUT_DIR / "ledger.json"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

STAKE = 1.0
ODDS = 100  # even money (+100); see module docstring


def american_profit(odds: int, stake: float = STAKE) -> float:
    """Win profit for a `stake` bet at American `odds` (loss is always -stake)."""
    return stake * odds / 100.0 if odds > 0 else stake * 100.0 / abs(odds)


def empty_ledger() -> dict:
    return {"bankroll": 0.0, "stake": STAKE, "odds_assumption": f"+{ODDS} (even money)",
            "record": {"wins": 0, "losses": 0, "picks": 0},
            "entries": []}


def load_ledger() -> dict:
    if LEDGER_PATH.exists():
        return json.loads(LEDGER_PATH.read_text())
    return empty_ledger()


def save_ledger(ledger: dict) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2))


def grade_date(date: str) -> list[dict]:
    """Settle the flagged picks in output/picks_<date>.json against final scores.
    Returns one entry per graded pick (skips games not yet final)."""
    picks_path = OUTPUT_DIR / f"picks_{date}.json"
    if not picks_path.exists():
        log.warning("no picks file for %s", date)
        return []
    payload = json.loads(picks_path.read_text())
    results = mlb_api.results_for(date)

    settled: list[dict] = []
    for g in payload.get("games", []):
        if not g.get("flagged"):
            continue
        res = results.get(g.get("game_pk"))
        if not res or not res["final"] or not res["winner"]:
            log.info("skip ungraded pick %s (%s)", g.get("pick"), g.get("matchup"))
            continue
        won = res["winner"] == g["pick"]
        settled.append({
            "key": f"{date}#{g['game_pk']}",
            "date": date,
            "matchup": g["matchup"],
            "pick": g["pick"],
            "result": "W" if won else "L",
            "score": f"{res['away']} {res['away_score']} @ {res['home']} {res['home_score']}",
            "odds": ODDS,
            "profit": round(american_profit(ODDS) if won else -STAKE, 2),
        })
    return settled


def update_ledger(date: str) -> dict:
    """Append a date's newly-final picks to the ledger. Idempotent per *pick*
    (by game_pk), so re-running a partially-complete day safely catches the
    games that have since gone final without double-counting settled ones."""
    ledger = load_ledger()
    done = {e["key"] for e in ledger["entries"]}

    added = 0
    for e in grade_date(date):
        if e["key"] in done:
            continue
        ledger["bankroll"] = round(ledger["bankroll"] + e["profit"], 2)
        ledger["record"]["wins" if e["result"] == "W" else "losses"] += 1
        ledger["record"]["picks"] += 1
        e["bankroll_after"] = ledger["bankroll"]
        ledger["entries"].append(e)
        added += 1

    if added:
        save_ledger(ledger)
        log.info("graded %s: +%d pick(s), bankroll now %+.2f",
                 date, added, ledger["bankroll"])
    else:
        log.info("nothing new to settle for %s", date)
    return ledger


def bankroll_line(ledger: dict | None = None) -> str:
    """One-line bankroll summary for the daily issue."""
    ledger = ledger or load_ledger()
    r = ledger["record"]
    return (f"**Running bankroll: {ledger['bankroll']:+.2f} units** "
            f"({r['wins']}-{r['losses']} on {r['picks']} picks, $1/pick at even money)")


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Grade picks + update the bankroll ledger")
    parser.add_argument("--date", default=os.environ.get("GRADE_DATE") or yesterday_eastern(),
                        help="date to grade (YYYY-MM-DD); default = yesterday US/Eastern")
    args = parser.parse_args()
    ledger = update_ledger(args.date)
    print(bankroll_line(ledger))


if __name__ == "__main__":
    main()
