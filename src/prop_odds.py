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
PRIORITY = {"bet": 0, "shadow": 1}      # lower spends first


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
    if rem <= RESERVE:
        log.warning("odds credits: %d left (reserve %d) - skipping %s fetch",
                    rem, RESERVE, tier)
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


def _as_row(v) -> dict:
    """Tolerate the OLD cache shape, which stored the over price as a bare int."""
    if isinstance(v, dict):
        return v
    if isinstance(v, (int, float)):
        return {"over": int(v)}
    return {}


def hit_line(date: str, player: str, away_name: str, home_name: str) -> int | None:
    """The real 1+ hit (Over 0.5) American price for a player, or None. Fetches a
    game's whole batter_hits board once per day and caches it (credit-thrifty)."""
    if not _key():
        return None
    cache = _load_cache(date)
    game_key = f"{away_name}@{home_name}"
    if game_key not in cache:
        eid = _event_id(date, away_name, home_name)
        cache[game_key] = _fetch_game_lines(eid) if eid else {}
        _save_cache(date, cache)
    return _as_row(cache[game_key].get(player.strip().lower())).get("over")


HRR_MARKET = "batter_hits_runs_rbis"
HRR_POINT = 1.5


def _hrr_cache_path(date: str) -> Path:
    return OUTPUT_DIR / f"prop_odds_hrr_{date}.json"


def _fetch_hrr_lines(event_id: str) -> dict:
    """{player lower: {"over": american, "under": american}} for the
    hits+runs+RBIs OVER/UNDER 1.5 line, median across books."""
    data = _get(f"/events/{event_id}/odds", regions="us", markets=HRR_MARKET,
                oddsFormat="american")
    sides: dict = {}
    for bk in (data or {}).get("bookmakers", []) or []:
        for mk in bk.get("markets", []) or []:
            if mk.get("key") != HRR_MARKET:
                continue
            for o in mk.get("outcomes", []) or []:
                side = str(o.get("name")).lower()
                if side not in ("over", "under") or o.get("point") != HRR_POINT:
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


def hrr_line(date: str, player: str, away_name: str, home_name: str) -> dict:
    """{"over", "under"} for a player's hits+runs+RBIs 1.5 line, or {}.

    SEPARATE MARKET, SEPARATE CREDIT. The Odds API bills per market, so this is
    one extra credit per game per day on top of batter_hits. It is therefore
    called for PLAYS ONLY - roughly 2-3 a day, about 80 credits a month against
    the ~150-240 free tier, where batter_hits already spends a similar amount.
    Calling it for every board game would bust the tier.

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
    return _as_row(cache[game_key].get(player.strip().lower()))


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
    return _as_row(cache[game_key].get(player.strip().lower()))


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
    return _as_row(cache[game_key].get(player.strip().lower()))
