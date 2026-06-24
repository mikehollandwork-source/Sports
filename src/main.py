"""
Entry point: build the daily edge list.

For each MLB game today:
  1. pull schedule + probable pitchers (MLB API)
  2. pull last-5-game hitting/pitching stats (MLB API)
  3. pull public majority from covers consensus + forum (covers.com)
  4. flag games where the statistically-advantaged team is NOT the public side

Writes output/picks_<date>.json. Date defaults to today (US/Eastern) and can be
overridden with --date YYYY-MM-DD or the PICKS_DATE env var.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import zoneinfo
from pathlib import Path

from . import covers
from .analysis import evaluate_game
from .mlb_api import enrich_with_stats, schedule_for

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")


def today_eastern() -> str:
    return dt.datetime.now(EASTERN).date().isoformat()


def run(date: str) -> dict:
    log.info("Building edge list for %s", date)

    games = schedule_for(date)
    log.info("Found %d games", len(games))
    if not games:
        return {"date": date, "games": [], "picks": [], "note": "no games scheduled"}

    # Public sentiment (fetched once, shared across games).
    consensus = covers.consensus()
    team_names = [t.name for g in games for t in (g.home, g.away)]
    forum_counts = covers.forum_majority(team_names, date)

    results = []
    for g in games:
        try:
            enrich_with_stats(g, date)
        except Exception as exc:
            log.warning("stats enrichment failed for %s: %s", g.game_pk, exc)
        results.append(evaluate_game(g, consensus, forum_counts))

    picks = [r["pick"] for r in results if r["flagged"]]
    log.info("Flagged %d edge game(s)", len(picks))

    return {
        "date": date,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "games": results,
        "picks": picks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="MLB public-vs-stats edge finder")
    parser.add_argument("--date", default=os.environ.get("PICKS_DATE") or today_eastern())
    args = parser.parse_args()

    payload = run(args.date)

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"picks_{args.date}.json"
    out_path.write_text(json.dumps(payload, indent=2))
    log.info("Wrote %s", out_path)
    print(json.dumps(payload.get("picks", []), indent=2))


if __name__ == "__main__":
    main()
