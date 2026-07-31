"""
Kalshi order-book logger - the missing half of the cross-venue comparison.

WHY THIS EXISTS
We have 15+ days of Polymarket order-book history (pm_books) and ZERO days of
Kalshi. src/kalshi.py can read Kalshi fine, but nothing ever recorded it, so the
"do both venues agree on where the money is?" question is unanswerable on
history. Depth is ephemeral - once a market moves, the old book is gone and
cannot be backfilled - so the only fix is to start logging now.

Mirrors pm_books deliberately: same cadence, same file shape, same per-game
readings list, so venue_agree.py can line the two up tick by tick.

output/kalshi_books_<date>.json:
  {date, games: {game_pk: {matchup, side, play, game_datetime, ticker,
                           readings: [{t, bid, bid_sz, ask, ask_sz} | {t, empty}]}}}

`side` is the board's advantage team, and the stored ticker is THAT team's
"wins" market, so bid = money backing our side and ask = money backing the
other - exactly the orientation pm_books uses. Fails soft everywhere: a Kalshi
outage must never touch the board.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import time
import zoneinfo
from pathlib import Path

from . import kalshi
from .analysis import _canon_abbr

log = logging.getLogger("kalshi_books")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")


def path_for(date: str) -> Path:
    return OUTPUT_DIR / f"kalshi_books_{date}.json"


def load_day(date: str) -> dict:
    try:
        return json.loads(path_for(date).read_text())
    except (OSError, ValueError):
        return {}


def run(date: str | None = None) -> int:
    """Append one Kalshi top-of-book reading per board game. Returns games logged."""
    date = date or dt.datetime.now(EASTERN).date().isoformat()
    picks_path = OUTPUT_DIR / f"picks_{date}.json"
    if not picks_path.exists():
        log.info("no picks file for %s", date)
        return 0
    try:
        games = json.loads(picks_path.read_text()).get("games", [])
    except ValueError:
        return 0
    try:
        markets = kalshi.game_markets()
    except Exception as exc:
        log.warning("kalshi markets fetch failed: %s", exc)
        return 0
    if not markets:
        log.warning("kalshi returned no active MLB markets (series=%s)", kalshi.SERIES)
        return 0
    log.info("kalshi: %d market keys, e.g. %s", len(markets),
             list(markets)[:5])

    day = load_day(date) or {"date": date, "games": {}}
    now = int(time.time())
    logged = 0
    missed: list = []
    for g in games:
        pc = g.get("pick_criteria") or {}
        adv = pc.get("advantage_team")
        matchup = g.get("matchup") or ""
        if not adv or " @ " not in matchup:
            continue
        aa, ha = _canon_abbr(g.get("away_abbr") or ""), _canon_abbr(g.get("home_abbr") or "")
        if not aa or not ha:
            continue
        pair = markets.get((aa, ha))
        if not pair:
            missed.append((aa, ha))
            continue
        away, home = matchup.split(" @ ")
        adv_abbr = ha if adv == home else aa
        ticker = pair.get(adv_abbr)
        if not ticker:
            continue
        try:
            book = kalshi.top_of_book(ticker) or {"empty": True}
        except Exception as exc:
            log.warning("kalshi book failed (%s): %s", ticker, exc)
            continue
        key = str(g.get("game_pk"))
        entry = day["games"].setdefault(key, {
            "matchup": matchup, "side": adv, "play": pc.get("play") == "pick",
            "game_datetime": g.get("game_datetime"), "ticker": ticker,
            "readings": [],
        })
        entry["play"] = pc.get("play") == "pick"      # keep current
        entry["readings"].append({"t": now, **book})
        logged += 1

    if missed:
        # the usual failure is an abbreviation mismatch (Kalshi codes vs ours),
        # so print both sides rather than a bare count
        log.warning("kalshi: no market for %d game(s), e.g. %s | kalshi has e.g. %s",
                    len(missed), missed[:5], list(markets)[:5])
    if logged:
        OUTPUT_DIR.mkdir(exist_ok=True)
        path_for(date).write_text(json.dumps(day, indent=1))
        log.info("kalshi books: logged %d game(s) -> %s", logged, path_for(date).name)
    return logged


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()


if __name__ == "__main__":
    main()
