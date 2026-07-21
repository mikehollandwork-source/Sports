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


def game_markets() -> dict:
    """{(abbr1, abbr2): {abbr: ticker}} for OPEN MLB game markets, keyed in both
    orders (a game's two 'TEAM wins' markets share an event_ticker)."""
    events: dict = {}
    cursor = None
    for _ in range(20):                    # paginate, hard-capped
        params = {"series_ticker": SERIES, "status": "open", "limit": 200}
        if cursor:
            params["cursor"] = cursor
        data = _get("/markets", **params)
        mkts = (data or {}).get("markets") or []
        for m in mkts:
            try:
                team = _name_abbr(str(m.get("yes_sub_title") or m.get("subtitle") or ""))
                ev = m.get("event_ticker")
                if team and ev and m.get("ticker"):
                    events.setdefault(ev, {})[team] = m["ticker"]
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
    log.info("kalshi: %d open game market pair(s)", len(index) // 2)
    return index


def top_of_book(ticker: str) -> dict | None:
    """{bid, ask, bid_sz, ask_sz} for a market's YES side, prices in 0-1.
    YES ask = 1 - best NO bid. Empty book -> {'empty': True}; failure -> None."""
    data = _get(f"/markets/{ticker}/orderbook")
    ob = (data or {}).get("orderbook")
    if ob is None:
        return None
    try:
        yes = [(int(p) / 100.0, int(q)) for p, q in ob.get("yes") or []]
        no = [(int(p) / 100.0, int(q)) for p, q in ob.get("no") or []]
    except Exception:
        return None
    if not yes and not no:
        return {"empty": True}
    out: dict = {}
    if yes:
        p, q = max(yes, key=lambda x: x[0])
        out["bid"], out["bid_sz"] = p, q
    if no:
        p, q = max(no, key=lambda x: x[0])
        out["ask"], out["ask_sz"] = round(1 - p, 2), q
    return out
