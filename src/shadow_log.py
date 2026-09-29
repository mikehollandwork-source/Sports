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

GRADING IS A SEPARATE PASS, AND HAS TO BE
Outcomes used to be written inside the reading loop, which meant they were only
ever captured in the narrow window where a game was already final AND its
markets were still quoting. They almost never are: once a game ends the Kalshi
and Polymarket markets settle, no reading attaches, the loop `continue`s, and
the outcome line is never reached. The logger also only walks TODAY's schedule,
so it never returned to a past date to finish the job.

The result was a log that captured order books it could never grade - 4 of 18
WNBA games had an outcome. A shadow ledger that never grades cannot produce the
sample it exists to produce, and the failure is silent, because the readings
keep accumulating and the files keep growing. `backfill` walks the existing
files and settles anything still open, independent of whether a market quotes.
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


SIDE_TOL = 0.12      # same tolerance pm_books uses to validate a token
MIN_SIZE = 50.0      # below this the quote is a placeholder, not a market


def _implied(ml) -> float:
    ml = int(ml)
    return 100.0 / (ml + 100) if ml > 0 else -ml / (-ml + 100.0)


def _pm_side(token: str, ref: float | None) -> dict:
    """Top-of-book for a PM token, validated against the book's implied price.

    Gamma's outcome->token pairing cannot be trusted blind - pm_books learned
    this the hard way and validates every token the same way. The first WNBA
    capture proved the point: Indiana at -220 (68.8% implied) came back from
    gamma at 0.49/0.50, a 19-point disagreement with both the sportsbook and
    Kalshi. Storing that unflagged would poison any later analysis with numbers
    that look real.

    Suspect quotes are RECORDED with a flag rather than dropped - knowing a
    token was wrong is itself data, and silently discarding it would hide how
    often gamma mispairs."""
    try:
        b = pm_books.best_of_book(token)
    except Exception as exc:
        log.warning("pm side failed: %s", exc)
        return {}
    if not b or b.get("empty"):
        return {}
    bid, ask = b.get("bid"), b.get("ask")
    if isinstance(bid, (int, float)) and isinstance(ask, (int, float)):
        mid = (bid + ask) / 2
        if ref is not None and abs(mid - ref) > SIDE_TOL:
            b["suspect"] = round(mid - ref, 3)
        if (ask - bid) > 0.15:
            b["wide"] = True
    if max(float(b.get("bid_sz") or 0), float(b.get("ask_sz") or 0)) < MIN_SIZE:
        b["thin"] = True
    return b


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
        # the book's implied price is the reference gamma's token is checked
        # against; without it a mispaired token is indistinguishable from a
        # genuine disagreement between venues
        bk = entry.get("book") or {}
        ref_a = _implied(bk[g["away"]]) if isinstance(bk.get(g["away"]), int) else None
        ref_h = _implied(bk[g["home"]]) if isinstance(bk.get(g["home"]), int) else None
        pa, ph = entry["pm"].get("away_token"), entry["pm"].get("home_token")
        if pa or ph:
            reading["p"] = {"away": _pm_side(pa, ref_a) if pa else {},
                            "home": _pm_side(ph, ref_h) if ph else {}}
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


# league_api.results_for asks the odds API for daysFrom=3, so a game can only be
# settled within roughly three days of being played. Older files are past
# recovery and are skipped rather than burning a call per file. This is why the
# backfill has to run DAILY to be worth anything - miss a week and that week is
# permanently ungraded.
RECOVERY_DAYS = 4


def backfill(sport: str, days: int = RECOVERY_DAYS) -> int:
    """Settle any logged game that still has no outcome. Idempotent.

    Runs over the files rather than over a schedule, so a game that went final
    while its markets were closed - which is every game - still gets graded."""
    import glob

    cutoff = (dt.datetime.now(EASTERN).date()
              - dt.timedelta(days=days)).isoformat()
    filled = 0
    for path in sorted(glob.glob(str(OUTPUT_DIR / f"shadow_{sport}_*.json"))):
        if Path(path).stem.split("_")[-1] < cutoff:
            continue
        try:
            day = json.loads(Path(path).read_text())
        except (OSError, ValueError):
            continue
        games = day.get("games") or {}
        open_ids = [gid for gid, e in games.items() if not (e.get("outcome") or {}).get("winner")]
        if not open_ids:
            continue
        try:
            results = league_api.results_for(sport, day.get("date") or "")
        except Exception as exc:
            log.warning("backfill results failed for %s: %s", day.get("date"), exc)
            continue
        hit = 0
        for gid in open_ids:
            res = results.get(gid) or results.get(int(gid) if gid.isdigit() else gid)
            if res and res.get("final") and res.get("winner"):
                games[gid]["outcome"] = {"winner": res["winner"],
                                         "away_score": res.get("away_score"),
                                         "home_score": res.get("home_score")}
                hit += 1
        if hit:
            Path(path).write_text(json.dumps(day, indent=1))
            filled += hit
            log.info("backfilled %d outcome(s) in %s", hit, Path(path).name)
    return filled


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "wnba"
    if sports.get(sport).live:
        log.warning("%s is live - shadow logging is for non-live sports", sport)
    # grade first: a game that ended yesterday is settled now, and waiting for
    # the reading loop to notice means waiting forever
    log.info("backfilled %d outcome(s)", backfill(sport))
    run(sport)


if __name__ == "__main__":
    main()
