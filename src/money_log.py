"""
Unified money log - the dataset a live-picks feature would need.

WHAT IT CAPTURES, per game, per tick, on BOTH venues
  * both sides (not just our advantage side), so "money on each side" is direct
  * top-of-book bid/ask + resting sizes (the instantaneous depth)
  * volume + open interest (the CUMULATIVE money that has traded / is at risk)
  * a phase tag: "pre" before first pitch, "live" after it
  * and, once the game is final, the outcome

The existing loggers were built for one job each and only record the advantage
side's contract pre-game. This records the full picture on a single timeline so a
future in-game feature can ask "has money moved decisively since first pitch?"
without any of the data being missing after the fact. Depth cannot be recovered
later, so anything not captured now is lost - hence recording more than today's
rules need.

output/money_<date>.json:
  {date, games: {game_pk: {matchup, away, home, game_datetime, outcome,
                           kalshi: {away_ticker, home_ticker},
                           pm: {away_token, home_token},
                           readings: [{t, phase,
                                       k: {away: {...}, home: {...}},
                                       p: {away: {...}, home: {...}}}]}}}

Runs on the same cadence as pm_books and fails soft at every level: a venue
outage degrades the record, it never breaks the board.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import time
import zoneinfo
from pathlib import Path

from . import kalshi, mlb_api, pm_books
from .analysis import _canon_abbr

log = logging.getLogger("money_log")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")


def path_for(date: str) -> Path:
    return OUTPUT_DIR / f"money_{date}.json"


def load_day(date: str) -> dict:
    try:
        return json.loads(path_for(date).read_text())
    except (OSError, ValueError):
        return {}


def _start_ts(iso) -> int | None:
    try:
        return int(dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def _kalshi_side(ticker: str) -> dict:
    """Book + cumulative money for one team's Kalshi market."""
    out: dict = {}
    try:
        book = kalshi.top_of_book(ticker)
        if book and not book.get("empty"):
            out.update(book)
        out.update(kalshi.money(ticker) or {})
    except Exception as exc:
        log.warning("kalshi side failed (%s): %s", ticker, exc)
    return out


def _pm_side(token: str) -> dict:
    """Top-of-book for one Polymarket outcome token."""
    try:
        b = pm_books.best_of_book(token)
        return b if b and not b.get("empty") else {}
    except Exception as exc:
        log.warning("pm side failed: %s", exc)
        return {}


def run(date: str | None = None) -> int:
    date = date or dt.datetime.now(EASTERN).date().isoformat()
    picks_path = OUTPUT_DIR / f"picks_{date}.json"
    if not picks_path.exists():
        return 0
    try:
        games = json.loads(picks_path.read_text()).get("games", [])
    except ValueError:
        return 0

    try:
        kmarkets = kalshi.game_markets()
    except Exception as exc:
        log.warning("kalshi markets failed: %s", exc)
        kmarkets = {}
    try:
        pindex = pm_books.open_market_index()
    except Exception as exc:
        log.warning("pm market index failed: %s", exc)
        pindex = {}
    try:
        results = mlb_api.results_for(date)
    except Exception:
        results = {}

    day = load_day(date) or {"date": date, "games": {}}
    now = int(time.time())
    logged = 0
    for g in games:
        matchup = g.get("matchup") or ""
        if " @ " not in matchup:
            continue
        away, home = matchup.split(" @ ")
        aa = _canon_abbr(g.get("away_abbr") or "")
        ha = _canon_abbr(g.get("home_abbr") or "")
        if not aa or not ha:
            continue
        key = str(g.get("game_pk"))
        start = _start_ts(g.get("game_datetime"))
        entry = day["games"].setdefault(key, {
            "matchup": matchup, "away": away, "home": home,
            "game_datetime": g.get("game_datetime"),
            "kalshi": {}, "pm": {}, "readings": [],
        })

        ktick = kmarkets.get((aa, ha)) or {}
        if ktick:
            entry["kalshi"] = {"away_ticker": ktick.get(aa), "home_ticker": ktick.get(ha)}
        ptok = pindex.get((aa, ha)) or {}
        if ptok:
            entry["pm"] = {"away_token": ptok.get(aa), "home_token": ptok.get(ha)}

        reading: dict = {"t": now,
                         "phase": "live" if (start and now >= start) else "pre"}
        k_away = entry["kalshi"].get("away_ticker")
        k_home = entry["kalshi"].get("home_ticker")
        if k_away or k_home:
            reading["k"] = {"away": _kalshi_side(k_away) if k_away else {},
                            "home": _kalshi_side(k_home) if k_home else {}}
        p_away = entry["pm"].get("away_token")
        p_home = entry["pm"].get("home_token")
        if p_away or p_home:
            reading["p"] = {"away": _pm_side(p_away) if p_away else {},
                            "home": _pm_side(p_home) if p_home else {}}
        if "k" not in reading and "p" not in reading:
            continue                       # nothing from either venue - skip
        entry["readings"].append(reading)

        res = results.get(g.get("game_pk"))
        if res and res.get("final") and res.get("winner"):
            entry["outcome"] = {"winner": res["winner"],
                                "away_score": res.get("away_score"),
                                "home_score": res.get("home_score")}
        logged += 1

    if logged:
        OUTPUT_DIR.mkdir(exist_ok=True)
        path_for(date).write_text(json.dumps(day, indent=1))
        log.info("money log: %d game(s) -> %s", logged, path_for(date).name)
    return logged


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()


if __name__ == "__main__":
    main()
