"""
Real 1+ HIT prop lines from The Odds API (batter_hits market), both sides.

A player's "1+ hit" price is the OVER 0.5 hits outcome. We only need lines for
the games that become PLAYS (~5-8/day), and a per-day cache
(output/prop_odds_<date>.json) means each game's odds are fetched at most once
per day and then frozen - so hourly board refreshes reuse the same line and we
stay well under the free tier (~150-240 credits/month).

Needs a free key in THE_ODDS_API_KEY. No key -> returns None everywhere and the
prop ledger falls back to its assumed price (fully optional, fail-soft). The
/events listing is free; only /events/{id}/odds spends a credit, so we fetch
that once per play-game per day.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import unicodedata
from pathlib import Path

import requests

from . import apitime

log = logging.getLogger("prop_odds")

BASE = "https://api.the-odds-api.com/v4/sports/baseball_mlb"
TIMEOUT = 15
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _key() -> str | None:
    return os.environ.get("THE_ODDS_API_KEY") or None


# CREDIT BUDGET.
#
# The Odds API bills one credit per MARKET per REGION on /events/{id}/odds, and
# reports the truth in response headers - x-requests-remaining and
# x-requests-used. Those are recorded rather than estimated, because an estimate
# of spend is exactly the thing that silently drifts until lines stop arriving
# and the ledger quietly falls back to its assumed -200.
#
# Measured on 104 days of boards: ~2.3 plays a day, so batter_hits ~72 a month,
# the H+R+RBI shadow ~70 and home runs ~70 = ~213 against a ~150-240 tier.
#
# So fetches are PRIORITISED. When remaining credits fall under RESERVE, only
# what is actually being BET still spends: the posted 1+ hit line and the home-run
# line, both of which are graded into the prop ledger. The H+R+RBI shadow - an
# experiment with nothing staked - is dropped first and automatically. That is
# how the same RESULTS survive a smaller budget: the experiment yields, the bets
# do not.
STATE = OUTPUT_DIR / "odds_credits.json"
RESERVE = int(os.environ.get("ODDS_RESERVE", "40"))
# Lower spends first. An UNREGISTERED tier falls to 0 below and is treated as a
# bet, so anything new that spends credits must be added here or it will outrank
# the posted bets and drain the budget they depend on.
# prop_extra: a hit line for a game that is NOT a model play. Those props are
# real bets and are graded, so they rank above the shadow experiment, but they
# are new games to price rather than second players on an already-paid-for
# board, so they yield before a play's own line does.
PRIORITY = {"bet": 0, "prop_extra": 1, "shadow": 2, "log": 3}


def _state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def _note_headers(r) -> None:
    """Record what the API itself says is left. Never estimated."""
    rem = r.headers.get("x-requests-remaining")
    used = r.headers.get("x-requests-used")
    if rem is None and used is None:
        return
    st = _state()
    try:
        if rem is not None:
            st["remaining"] = int(float(rem))
        if used is not None:
            st["used"] = int(float(used))
    except (TypeError, ValueError):
        return
    st["last_seen"] = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(st, indent=1))
    except OSError:
        pass


def remaining() -> int | None:
    """Credits the API last said were left, or None if never seen."""
    v = _state().get("remaining")
    return int(v) if isinstance(v, (int, float)) else None


def may_spend(tier: str = "bet") -> bool:
    """Whether a fetch of this tier should go ahead.

    Unknown remaining -> allow: refusing on no information would silently stop
    the board getting prices it has always had.
    """
    if PRIORITY.get(tier, 0) == 0:
        return True                     # a bet's price always spends
    rem = remaining()
    if rem is None:
        return True
    # The reserve scales with priority, so the tiers yield in order rather than
    # all stopping at the same line: shadow holds back 40, plain logging 80.
    floor = RESERVE * PRIORITY.get(tier, 0)
    if rem <= floor:
        log.warning("odds credits: %d left (floor %d for %s) - skipping fetch",
                    rem, floor, tier)
        return False
    return True


def _get(path: str, **params):
    try:
        with apitime.timed("oddsapi", path):
            r = requests.get(f"{BASE}{path}", params={"apiKey": _key(), **params}, timeout=TIMEOUT)
            _note_headers(r)
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        log.warning("odds-api fetch failed (%s): %s", path, exc)
        return None


def _cache_path(date: str) -> Path:
    return OUTPUT_DIR / f"prop_odds_{date}.json"


def _load_cache(date: str) -> dict:
    try:
        return json.loads(_cache_path(date).read_text())
    except (OSError, ValueError):
        return {}


def _save_cache(date: str, cache: dict) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    _cache_path(date).write_text(json.dumps(cache, indent=1))


_EVENTS: dict = {}   # date -> [{id, home, away}] (free listing, cached per process)


def _events(date: str) -> list:
    if date in _EVENTS:
        return _EVENTS[date]
    data = _get("/events", dateFormat="iso")
    evs = [{"id": e.get("id"), "home": e.get("home_team"), "away": e.get("away_team")}
           for e in (data or []) if e.get("id")]
    _EVENTS[date] = evs
    return evs


def _event_id(date: str, away_name: str, home_name: str) -> str | None:
    for e in _events(date):
        if e["home"] == home_name and e["away"] == away_name:
            return e["id"]
    return None


def _fetch_game_lines(event_id: str) -> dict:
    """{player_name_lower: {"over": american, "under": american}} for a game's
    batter_hits 0.5 line, median across books. {} on failure/none.

    BOTH SIDES, because the same response already contains them and the UNDER
    costs no extra credit. Without it the question "what would fading these
    return" can only be answered from an ASSUMED hold, and the answer swings from
    break-even at a 4% hold to -5% at 6% - i.e. the assumption decides it.
    """
    data = _get(f"/events/{event_id}/odds", regions="us", markets="batter_hits",
                oddsFormat="american")
    sides: dict = {}
    for bk in (data or {}).get("bookmakers", []) or []:
        for mk in bk.get("markets", []) or []:
            if mk.get("key") != "batter_hits":
                continue
            for o in mk.get("outcomes", []) or []:
                side = str(o.get("name")).lower()
                if side not in ("over", "under") or o.get("point") != 0.5:
                    continue
                who = str(o.get("description") or "").strip().lower()
                if who and isinstance(o.get("price"), (int, float)):
                    sides.setdefault(who, {}).setdefault(side, []).append(
                        int(o["price"]))
    out: dict = {}
    for who, bysides in sides.items():
        row = {}
        for side, v in bysides.items():
            if v:
                row[side] = int(sorted(v)[len(v) // 2])
        if row.get("over") is not None:
            out[who] = row
    return out


def _fold(name: str) -> str:
    """A name in the one shape both feeds agree on: unaccented, punctuation-free.

    THE TWO FEEDS DISAGREE ON ACCENTS IN BOTH DIRECTIONS. The Odds API served
    `jose ramirez` while MLB says `Jose\u0301 Rami\u0301rez`, and it served
    `agusti\u0301n rami\u0301rez` while it served `ronald acuna jr.` for a man MLB
    spells `Acun\u0303a`. So neither side can be treated as canonical and a bare
    `.lower()` misses whichever way the pair happens to fall.

    Measured on the cached boards: 32 of 499 names (6.4%) cannot match on
    `.lower()` alone - every accent, every `J.P.`/`A.J.`, every `(2002)`
    disambiguator. It is not cosmetic. On 2026-10-13 Jose\u0301 Rami\u0301rez's real
    -193 (break-even 65.9%) sat in the cache under `jose ramirez` while the
    lookup missed it, fell back to the assumed -200 (66.7%) and withheld a
    66.3% read by four tenths of a point.
    """
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\(.*?\)", " ", s)          # `max muncy (2002)` disambiguator
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _row_for(board: dict, player: str) -> dict:
    """The player's row from a cached game board, matched on the folded name.

    Exact first so nothing already working changes, then the fold. Caches
    written before this are matched the same way, since the fold is computed
    on read rather than stored.
    """
    if not isinstance(board, dict):
        return {}
    lo = str(player).strip().lower()
    if lo in board:
        return _as_row(board[lo])
    want = _fold(player)
    if not want:
        return {}
    for k, v in board.items():
        if _fold(k) == want:
            return _as_row(v)
    return {}


def _as_row(v) -> dict:
    """Tolerate the OLD cache shape, which stored the over price as a bare int."""
    if isinstance(v, dict):
        return v
    if isinstance(v, (int, float)):
        return {"over": int(v)}
    return {}


def hit_line(date: str, player: str, away_name: str, home_name: str,
             tier: str = "bet") -> int | None:
    """The real 1+ hit (Over 0.5) American price for a player, or None. Fetches a
    game's whole batter_hits board once per day and caches it (credit-thrifty).

    `tier` is only consulted when the game is not already cached, since a cached
    board costs nothing - so the second and third prop on one game never yield,
    only the first prop of a new game.
    """
    if not _key():
        return None
    cache = _load_cache(date)
    game_key = f"{away_name}@{home_name}"
    if game_key not in cache:
        if not may_spend(tier):
            return None
        eid = _event_id(date, away_name, home_name)
        cache[game_key] = _fetch_game_lines(eid) if eid else {}
        _save_cache(date, cache)
    return _row_for(cache[game_key], player).get("over")


HRR_MARKET = "batter_hits_runs_rbis"
HRR_POINT = 1.5


def _hrr_cache_path(date: str) -> Path:
    return OUTPUT_DIR / f"prop_odds_hrr_{date}.json"


def _fetch_player_ou(event_id: str, market: str, point: float) -> dict:
    """{player lower: {"over": american, "under": american}} for one player
    OVER/UNDER market at one point, median across books.

    Shared by the hits+runs+RBIs and total-bases fetchers, which differ only in
    the market key and the number.
    """
    data = _get(f"/events/{event_id}/odds", regions="us", markets=market,
                oddsFormat="american")
    sides: dict = {}
    for bk in (data or {}).get("bookmakers", []) or []:
        for mk in bk.get("markets", []) or []:
            if mk.get("key") != market:
                continue
            for o in mk.get("outcomes", []) or []:
                side = str(o.get("name")).lower()
                if side not in ("over", "under") or o.get("point") != point:
                    continue
                who = str(o.get("description") or "").strip().lower()
                if who and isinstance(o.get("price"), (int, float)):
                    sides.setdefault(who, {}).setdefault(side, []).append(
                        int(o["price"]))
    out: dict = {}
    for who, bysides in sides.items():
        row = {s: int(sorted(v)[len(v) // 2]) for s, v in bysides.items() if v}
        if row.get("over") is not None:
            out[who] = row
    return out


def _fetch_hrr_lines(event_id: str) -> dict:
    return _fetch_player_ou(event_id, HRR_MARKET, HRR_POINT)


def hrr_line(date: str, player: str, away_name: str, home_name: str) -> dict:
    """{"over", "under"} for a player's hits+runs+RBIs 1.5 line, or {}.

    SEPARATE MARKET, SEPARATE CREDIT. The Odds API bills per market, so this is
    one extra credit per game per day on top of batter_hits, and the per-day
    cache means repeat board runs cost nothing.

    IT IS NOW CAPTURED FOR EVERY GAME, not plays only, bounded by
    `WARM_MAX_GAMES`. That changed because `leg_markets.md` found the whole
    H+R+RBI question turns on the PRICE sample: the rate side is solid over
    1571 held-out games, while the price side was 42 quotes from four October
    dates, which is why a +4.1-point pooled edge could not be established.
    Collecting prices is the binding constraint, and the cap keeps a full
    regular-season slate from busting the tier.

    Why this market: 1+ hit is a ~63% event priced near -200, where break-even is
    66.7% and the hold eats any edge the hitter read could produce. H+R+RBI over
    1.5 was quoted at +105 on 2026-10-03, a 48.8% break-even - the same read with
    16 points less hold to overcome. Whether the read transfers is unknown, which
    is exactly why this is logged and not bet.

    Cached in its own day file so the batter_hits cache shape is untouched.
    """
    if not _key() or not may_spend("shadow"):
        return {}
    try:
        cache = json.loads(_hrr_cache_path(date).read_text())
    except (OSError, ValueError):
        cache = {}
    game_key = f"{away_name}@{home_name}"
    if game_key not in cache:
        eid = _event_id(date, away_name, home_name)
        cache[game_key] = _fetch_hrr_lines(eid) if eid else {}
        OUTPUT_DIR.mkdir(exist_ok=True)
        _hrr_cache_path(date).write_text(json.dumps(cache, indent=1))
    return _row_for(cache[game_key], player)


TB_MARKET = "batter_total_bases"
TB_POINT = 1.5            # "2+ total bases" is the OVER 1.5 outcome

# How many games a day get their H+R+RBI and total-bases boards captured.
# Postseason slates are 1-4 games, so this covers them in full; it exists so a
# fifteen-game regular-season slate cannot quietly spend 30 credits a day.
WARM_MAX_GAMES = int(os.environ.get("PROP_WARM_MAX", "4"))


def _tb_cache_path(date: str) -> Path:
    return OUTPUT_DIR / f"prop_odds_tb_{date}.json"


def tb_line(date: str, player: str, away_name: str, home_name: str) -> dict:
    """{"over", "under"} for a player's 2+ total bases, or {}.

    NO PRICE FOR THIS MARKET EXISTED ANYWHERE in the repo before this, which
    `leg_markets.md` called the single highest-value thing left to collect: the
    board's posted hitters reach 2+ total bases 36.4% of the time (fair about
    +175) and whether it is sold near fair was simply unknown.
    """
    if not _key() or not may_spend("log"):
        return {}
    try:
        cache = json.loads(_tb_cache_path(date).read_text())
    except (OSError, ValueError):
        cache = {}
    game_key = f"{away_name}@{home_name}"
    if game_key not in cache:
        eid = _event_id(date, away_name, home_name)
        cache[game_key] = (_fetch_player_ou(eid, TB_MARKET, TB_POINT)
                           if eid else {})
        OUTPUT_DIR.mkdir(exist_ok=True)
        _tb_cache_path(date).write_text(json.dumps(cache, indent=1))
    return _row_for(cache[game_key], player)


def warm(date: str, away_name: str, home_name: str) -> None:
    """Capture this game's H+R+RBI and total-bases boards for the day.

    Both are per-day cached, so the first board run of the day pays two credits
    for the game and every later run pays nothing. Returns nothing: the point
    is the cached board, which is what a later backtest reads.
    """
    for fn in (hrr_line, tb_line):
        try:
            fn(date, "", away_name, home_name)
        except Exception as exc:
            log.warning("price warm failed for %s@%s: %s",
                        away_name, home_name, exc)


HR_MARKET = "batter_home_runs"
HR_POINT = 0.5


def _hr_cache_path(date: str) -> Path:
    return OUTPUT_DIR / f"prop_odds_hr_{date}.json"


def hr_line(date: str, player: str, away_name: str, home_name: str) -> dict:
    """{"over", "under"} for a player's 1+ HOME RUN line, or {}.

    SEPARATE MARKET, SEPARATE CREDIT - see hrr_line. Plays only.
    """
    if not _key():
        return {}
    try:
        cache = json.loads(_hr_cache_path(date).read_text())
    except (OSError, ValueError):
        cache = {}
    game_key = f"{away_name}@{home_name}"
    if game_key not in cache:
        eid = _event_id(date, away_name, home_name)
        rows: dict = {}
        if eid:
            data = _get(f"/events/{eid}/odds", regions="us", markets=HR_MARKET,
                        oddsFormat="american")
            sides: dict = {}
            for bk in (data or {}).get("bookmakers", []) or []:
                for mk in bk.get("markets", []) or []:
                    if mk.get("key") != HR_MARKET:
                        continue
                    for o in mk.get("outcomes", []) or []:
                        side = str(o.get("name")).lower()
                        if side not in ("over", "under") \
                                or o.get("point") != HR_POINT:
                            continue
                        who = str(o.get("description") or "").strip().lower()
                        if who and isinstance(o.get("price"), (int, float)):
                            sides.setdefault(who, {}).setdefault(
                                side, []).append(int(o["price"]))
            for who, bys in sides.items():
                row = {sd: int(sorted(v)[len(v) // 2]) for sd, v in bys.items() if v}
                if row.get("over") is not None:
                    rows[who] = row
        cache[game_key] = rows
        OUTPUT_DIR.mkdir(exist_ok=True)
        _hr_cache_path(date).write_text(json.dumps(cache, indent=1))
    return _row_for(cache[game_key], player)


def hit_sides(date: str, player: str, away_name: str, home_name: str) -> dict:
    """{"over": american, "under": american} for a player's 0.5 hits line.

    Same cached fetch `hit_line` uses, so asking for both costs nothing extra.
    {} when there is no key, no line, or the player is not quoted.
    """
    if not _key():
        return {}
    cache = _load_cache(date)
    game_key = f"{away_name}@{home_name}"
    if game_key not in cache:
        eid = _event_id(date, away_name, home_name)
        cache[game_key] = _fetch_game_lines(eid) if eid else {}
        _save_cache(date, cache)
    return _row_for(cache[game_key], player)


def credits_check() -> str:
    """What the API says is left, via the FREE /events listing.

    /events costs nothing - only /events/{id}/odds is billed - so this reports
    the real remaining balance without spending a credit to find out.
    """
    if not _key():
        return "no THE_ODDS_API_KEY in the environment"
    _get("/events", dateFormat="iso")          # free; headers recorded
    st = _state()
    rem, used = st.get("remaining"), st.get("used")
    if rem is None and used is None:
        return "the API returned no credit headers"
    total = (rem + used) if isinstance(rem, int) and isinstance(used, int) else None
    bits = [f"remaining **{rem}**", f"used **{used}**"]
    if total is not None:
        bits.append(f"so the period allowance is **{total}**")
    bits.append(f"reserve is {RESERVE}")
    return " · ".join(bits)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    line = credits_check()
    print(line)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "odds_credits.md").write_text(
        f"# Odds API credits\n\n- {line}\n")


if __name__ == "__main__":
    main()
