"""
Kalshi (CFTC-regulated prediction market) MLB game markets - read-only.

Kalshi lists two markets per MLB game (one 'Will TEAM win?' per side) under a
game series. We read the public trade-api market list + order books so the
pm_books poller can record Kalshi's top-of-book next to Polymarket's for the
same games - answering 'which venue sells our side cheaper at entry, and which
has the deeper live book to exit into?'.

Kalshi books quote YES bids and NO bids in cents: the YES ask is 100 minus the
best NO bid. Endpoints/series naming are UNVERIFIED until the first Actions
run (set KALSHI_DEBUG=1 to dump raw JSON) and everything fails soft.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import requests

from .public_sources import _name_abbr
from .analysis import _canon_abbr
from . import apitime

log = logging.getLogger("kalshi")

BASE = "https://api.elections.kalshi.com/trade-api/v2"
SERIES = "KXMLBGAME"      # Kalshi's MLB game-winner series (best-effort guess)
TIMEOUT = 15
DEBUG = os.environ.get("KALSHI_DEBUG") == "1"
DEBUG_DIR = Path("output/kalshi_debug")


def _get(path: str, **params):
    try:
        with apitime.timed("kalshi", path):
            r = requests.get(f"{BASE}{path}", params=params, timeout=TIMEOUT,
                             headers={"User-Agent": "mlb-edge-finder (personal research)",
                                      "Accept": "application/json"})
            r.raise_for_status()
            data = r.json()
        if DEBUG:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            name = (path.strip("/").replace("/", "_") or "root") + ".json"
            (DEBUG_DIR / name).write_text(json.dumps(data)[:800000])
        return data
    except Exception as exc:
        log.warning("kalshi fetch failed (%s %s): %s", path, params, exc)
        return None


def _abbr(ticker: str) -> str | None:
    """The team this YES market resolves for, from the ticker suffix:
    'KXMLBGAME-26JUL231840KCDET-KC' -> 'KC' (canonicalized)."""
    tail = (ticker or "").rsplit("-", 1)[-1].upper()
    return _canon_abbr(tail) if tail else None


def _book(m: dict) -> dict:
    """Top-of-book for a market row: YES bid/ask (dollars, 0-1) + sizes, straight
    off the market object. Empty book -> {'empty': True}."""
    bid, ask = m.get("yes_bid_dollars"), m.get("yes_ask_dollars")
    if not bid and not ask:
        return {"empty": True}
    out: dict = {}
    if bid:
        out["bid"], out["bid_sz"] = float(bid), float(m.get("yes_bid_size_fp") or 0)
    if ask:
        out["ask"], out["ask_sz"] = float(ask), float(m.get("yes_ask_size_fp") or 0)
    return out


def game_markets() -> dict:
    """{(abbr1, abbr2): {abbr: ticker}} for ACTIVE MLB game markets, keyed in both
    orders (a game's two 'TEAM wins' markets share an event_ticker). Caches each
    market row's inline prices for same-tick reads via top_of_book()."""
    global _MARKET_CACHE
    _MARKET_CACHE = {}
    events: dict = {}
    cursor = None
    for _ in range(20):                    # paginate, hard-capped
        params = {"series_ticker": SERIES, "status": "active", "limit": 200}
        if cursor:
            params["cursor"] = cursor
        data = _get("/markets", **params)
        mkts = (data or {}).get("markets") or []
        for m in mkts:
            try:
                tk = m.get("ticker")
                team = _abbr(tk)
                ev = m.get("event_ticker")
                if team and ev and tk:
                    events.setdefault(ev, {})[team] = tk
                    _MARKET_CACHE[tk] = m
            except Exception:
                continue
        cursor = (data or {}).get("cursor")
        if not cursor or not mkts:
            break
        time.sleep(0.2)
    index: dict = {}
    for tick_by_team in events.values():
        abbrs = list(tick_by_team)
        if len(abbrs) == 2:
            index[(abbrs[0], abbrs[1])] = tick_by_team
            index[(abbrs[1], abbrs[0])] = tick_by_team
    log.info("kalshi: %d active game market pair(s)", len(index) // 2)
    return index


_MARKET_CACHE: dict = {}


def top_of_book(ticker: str) -> dict | None:
    """{bid, ask, bid_sz, ask_sz} for a market's YES side (prices 0-1). Uses the
    cached row from the last game_markets() pass; on a miss (or for a fresh
    reading) fetches the single market. Empty book -> {'empty': True}; None on
    failure."""
    m = _MARKET_CACHE.get(ticker)
    if m is None:
        data = _get(f"/markets/{ticker}")
        m = (data or {}).get("market")
        if m is None:
            return None
    return _book(m)
