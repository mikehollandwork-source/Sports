"""
Real 1+ HIT prop lines from The Odds API (batter_hits market).

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


def _get(path: str, **params):
    try:
        with apitime.timed("oddsapi", path):
            r = requests.get(f"{BASE}{path}", params={"apiKey": _key(), **params}, timeout=TIMEOUT)
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
    """{player_name_lower: over_0.5_american} for a game's batter_hits market,
    median across books. {} on failure/none."""
    data = _get(f"/events/{event_id}/odds", regions="us", markets="batter_hits",
                oddsFormat="american")
    prices: dict = {}
    for bk in (data or {}).get("bookmakers", []) or []:
        for mk in bk.get("markets", []) or []:
            if mk.get("key") != "batter_hits":
                continue
            for o in mk.get("outcomes", []) or []:
                if str(o.get("name")).lower() != "over" or o.get("point") != 0.5:
                    continue
                who = str(o.get("description") or "").strip().lower()
                if who and isinstance(o.get("price"), (int, float)):
                    prices.setdefault(who, []).append(int(o["price"]))
    return {who: int(sorted(v)[len(v) // 2]) for who, v in prices.items() if v}


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
    return cache[game_key].get(player.strip().lower())
