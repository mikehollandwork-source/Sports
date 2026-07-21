"""
Pinnacle (sharp-origin book) moneylines via the guest web API - best effort.

Pinnacle is a market-making book: its overnight number is the closest free proxy
to the low-limit "test line" sharps shoot at before retail books copy it. The
guest API is the unauthenticated endpoint pinnacle.com's own web app calls; the
X-API-Key below is the public client key shipped in that web bundle (not an
account secret). Like covers/ESPN, this endpoint is UNVERIFIED until the first
Actions run, and every parser fails soft (log a warning, return empty) so the
pipeline never depends on it.
"""

from __future__ import annotations

import logging

import requests

from . import apitime

log = logging.getLogger("pinnacle")

MLB_LEAGUE = 246   # Pinnacle's league id for MLB
BASE = "https://guest.api.arcadia.pinnacle.com/0.1"
HEADERS = {
    "User-Agent": "mlb-edge-finder (personal research)",
    # public client key from the pinnacle.com web bundle - not an account secret
    "X-API-Key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R",
    "Accept": "application/json",
}


def _get(path: str):
    try:
        with apitime.timed("pinnacle", path):
            r = requests.get(f"{BASE}{path}", headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json()
    except Exception as exc:  # network/HTTP/JSON - degrade gracefully
        log.warning("pinnacle fetch failed (%s): %s", path, exc)
        return None


def lines() -> list[dict]:
    """[{away_name, home_name, away_ml, home_ml, start}] for MLB games currently
    on Pinnacle's board (full-game moneyline, full team names). Empty on any
    failure - callers must treat this as optional."""
    matchups = _get(f"/leagues/{MLB_LEAGUE}/matchups")
    markets = _get(f"/leagues/{MLB_LEAGUE}/markets/straight")
    teams: dict = {}
    for m in matchups if isinstance(matchups, list) else []:
        try:
            # plain game matchups only: no props/alt-line children
            if m.get("parent") or m.get("type") not in (None, "matchup"):
                continue
            parts = {p.get("alignment"): p.get("name") for p in m.get("participants", [])}
            if parts.get("home") and parts.get("away"):
                teams[m["id"]] = {"away_name": parts["away"], "home_name": parts["home"],
                                  "start": m.get("startTime")}
        except Exception:
            continue
    out: list[dict] = []
    for mk in markets if isinstance(markets, list) else []:
        try:
            if mk.get("type") != "moneyline" or mk.get("period") != 0:
                continue
            t = teams.get(mk.get("matchupId"))
            if not t:
                continue
            prices = {p.get("designation"): p.get("price") for p in mk.get("prices", [])}
            if prices.get("away") is None or prices.get("home") is None:
                continue
            out.append({**t, "away_ml": int(prices["away"]), "home_ml": int(prices["home"])})
        except Exception:
            continue
    log.info("pinnacle: parsed %d game line(s)", len(out))
    return out
