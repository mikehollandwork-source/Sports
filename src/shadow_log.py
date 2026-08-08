"""
Shadow recorder for a non-live sport: capture everything a rule would need,
decide nothing.

WHAT THIS IS NOT
It is not a board. The MLB consensus rule needs covers.com ticket percentages,
VSiN handle, a forum tally and an MLB-specific stat model (wOBA/FIP/BvP/park) -
none of which exist for the WNBA. Shipping a "WNBA board" today would mean
inventing a rule and running it live, which is exactly the move that has failed
seven times this session.

WHAT IT IS
The data collection that makes a rule possible later. Every game, every ~10
minutes: both venues, both sides, book moneylines, a pre/live phase tag, and the
outcome once final. Order-book depth cannot be reconstructed after the fact, so
anything not captured now is gone - which is why this starts before there is
anything to test.

Because the sport's holdout begins the day logging starts, every game recorded
here is out-of-sample by construction. There is no history to fit to, which is
the single biggest methodological upgrade over how MLB was developed.

output/shadow_<sport>_<date>.json:
  {sport, date, games: {game_id: {matchup, away, home, away_abbr, home_abbr,
                                  start_ts, book: {team: american},
                                  outcome: {...},
                                  readings: [{t, phase,
                                              k: {away: {...}, home: {...}},
                                              p: {away: {...}, home: {...}}}]}}}

Fails soft at every level: a venue outage degrades the record, it never raises.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import statistics as st
import time
import zoneinfo
from pathlib import Path

from . import kalshi, league_api, pm_books, sports

log = logging.getLogger("shadow_log")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")


def path_for(sport: str, date: str) -> Path:
    return OUTPUT_DIR / f"shadow_{sport}_{date}.json"


def load_day(sport: str, date: str) -> dict:
    try:
        return json.loads(path_for(sport, date).read_text())
    except (OSError, ValueError):
        return {}


def moneylines(sport: str) -> dict:
    """{game_id: {team_name: median american}} across US books.

    Median rather than best price: one book with a stale line would otherwise
    define the whole market, and this is a record of what the market thought,
    not a shopping list."""
    sp = sports.get(sport)
    out: dict = {}
    for ev in league_api._get("/odds", sp.odds_key, regions="us", markets="h2h",
                              oddsFormat="american") or []:
        prices: dict = {}
        for bk in ev.get("bookmakers") or []:
            for mk in bk.get("markets") or []:
                if mk.get("key") != "h2h":
                    continue
                for oc in mk.get("outcomes") or []:
                    nm, pr = oc.get("name"), oc.get("price")
                    if nm and isinstance(pr, int):
                        prices.setdefault(nm, []).append(pr)
        if prices:
            out[ev.get("id")] = {k: int(st.median(v)) for k, v in prices.items()}
    return out


def _kalshi_side(ticker: str) -> dict:
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
    try:
        b = pm_books.best_of_book(token)
        return b if b and not b.get("empty") else {}
    except Exception as exc:
        log.warning("pm side failed: %s", exc)
        return {}


def run(sport: str = "wnba", date: str | None = None) -> int:
    sp = sports.get(sport)
    date = date or dt.datetime.now(EASTERN).date().isoformat()

    games = league_api.schedule(sport, date)
    if not games:
        log.info("no %s games scheduled for %s", sp.name, date)
        return 0

    try:
        kmarkets = kalshi.game_markets(sp.kalshi_series)
    except Exception as exc:
        log.warning("kalshi markets failed: %s", exc)
        kmarkets = {}
    try:
        pindex = pm_books.open_market_index(
            tag=sp.pm_tag, name_fn=lambda t: league_api.name_abbr(sport, t))
    except Exception as exc:
        log.warning("pm index failed: %s", exc)
        pindex = {}
    try:
        books = moneylines(sport)
    except Exception as exc:
        log.warning("moneylines failed: %s", exc)
        books = {}
    try:
        results = league_api.results_for(sport, date)
    except Exception:
        results = {}

    day = load_day(sport, date) or {"sport": sport, "date": date, "games": {}}
    now = int(time.time())
    logged = 0

    for g in games:
        gid = str(g["game_id"])
        aa, ha = g["away_abbr"], g["home_abbr"]
        entry = day["games"].setdefault(gid, {
            "matchup": g["matchup"], "away": g["away"], "home": g["home"],
            "away_abbr": aa, "home_abbr": ha,
            "start_ts": g["start_ts"], "game_datetime": g["game_datetime"],
            "kalshi": {}, "pm": {}, "readings": [],
        })
        if books.get(g["game_id"]):
            entry["book"] = books[g["game_id"]]

        ktick = kmarkets.get((aa, ha)) or {}
        if ktick:
            entry["kalshi"] = {"away_ticker": ktick.get(aa),
                               "home_ticker": ktick.get(ha)}
        ptok = pindex.get((aa, ha)) or {}
        if ptok:
            entry["pm"] = {"away_token": ptok.get(aa), "home_token": ptok.get(ha)}

        start = g.get("start_ts")
        reading: dict = {"t": now,
                         "phase": "live" if (start and now >= start) else "pre"}
        ka, kh = entry["kalshi"].get("away_ticker"), entry["kalshi"].get("home_ticker")
        if ka or kh:
            reading["k"] = {"away": _kalshi_side(ka) if ka else {},
                            "home": _kalshi_side(kh) if kh else {}}
        pa, ph = entry["pm"].get("away_token"), entry["pm"].get("home_token")
        if pa or ph:
            reading["p"] = {"away": _pm_side(pa) if pa else {},
                            "home": _pm_side(ph) if ph else {}}
        if "k" not in reading and "p" not in reading:
            continue
        entry["readings"].append(reading)

        res = results.get(g["game_id"])
        if res and res.get("final") and res.get("winner"):
            entry["outcome"] = {"winner": res["winner"],
                                "away_score": res.get("away_score"),
                                "home_score": res.get("home_score")}
        logged += 1

    if logged:
        OUTPUT_DIR.mkdir(exist_ok=True)
        path_for(sport, date).write_text(json.dumps(day, indent=1))
        log.info("%s shadow: %d game(s) -> %s", sp.name, logged,
                 path_for(sport, date).name)
    return logged


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "wnba"
    if sports.get(sport).live:
        log.warning("%s is live - shadow logging is for non-live sports", sport)
    run(sport)


if __name__ == "__main__":
    main()
