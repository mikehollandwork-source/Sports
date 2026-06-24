"""
Opponent strength (strength-of-schedule) data.

Fetches, once per run and cached:
  - every team's season win% (a single standings call)
  - every team's season wOBA and FIP (one call per team, cached)

The raw numbers are returned here; the *factor* math (how strength scales runs /
wOBA / FIP) lives in analysis.py next to the league baselines, so the whole
formula stays in one place. All lookups fail soft to None -> neutral factors.
"""

from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger("strength")

BASE = "https://statsapi.mlb.com/api/v1"
TIMEOUT = 20
POLITE_DELAY = 0.1
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "mlb-edge-finder/1.0"})

# win% varies by as-of date (standings snapshot); season wOBA/FIP are cumulative
# season totals (stable), cached separately so the backtest fetches each once.
_WINPCT: dict[str, dict[int, float]] = {}   # as_of_key -> {team_id: win_pct}
_SEASON: dict[int, dict] = {}               # team_id -> {woba, fip}


def _get(path: str, **params) -> dict:
    resp = SESSION.get(f"{BASE}/{path}", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    time.sleep(POLITE_DELAY)
    return resp.json()


def _winpct(season: int, as_of: str | None) -> dict[int, float]:
    """{team_id: win_pct} as of `as_of` (or current). Standings supports a date
    snapshot, so the backtest gets point-in-time records."""
    key = as_of or "now"
    if key in _WINPCT:
        return _WINPCT[key]
    table: dict[int, float] = {}
    try:
        params = {"leagueId": "103,104", "season": season}
        if as_of:
            params["date"] = as_of
        data = _get("standings", **params)
        for rec in data.get("records", []):
            for tr in rec.get("teamRecords", []):
                tid = tr["team"]["id"]
                pct = tr.get("winningPercentage")
                if pct is None:
                    w, l = tr.get("wins", 0), tr.get("losses", 0)
                    pct = w / (w + l) if (w + l) else 0.5
                table[tid] = float(pct)
    except Exception as exc:
        log.warning("standings (win%%) load failed for %s: %s", key, exc)
    _WINPCT[key] = table
    return table


def _woba(stat: dict) -> float | None:
    from .analysis import WOBA_W
    ab = float(stat.get("atBats", 0) or 0)
    bb = float(stat.get("baseOnBalls", 0) or 0)
    hbp = float(stat.get("hitByPitch", 0) or 0)
    sf = float(stat.get("sacFlies", 0) or 0)
    den = ab + bb + sf + hbp
    if den <= 0:
        return None
    h = float(stat.get("hits", 0) or 0)
    b2 = float(stat.get("doubles", 0) or 0)
    b3 = float(stat.get("triples", 0) or 0)
    hr = float(stat.get("homeRuns", 0) or 0)
    singles = h - b2 - b3 - hr
    return (WOBA_W["bb"] * bb + WOBA_W["hbp"] * hbp + WOBA_W["1b"] * singles
            + WOBA_W["2b"] * b2 + WOBA_W["3b"] * b3 + WOBA_W["hr"] * hr) / den


def _fip(stat: dict) -> float | None:
    from .analysis import FIP_CONSTANT
    ip_raw = str(stat.get("inningsPitched", "0") or "0")
    if "." in ip_raw:
        whole, frac = ip_raw.split(".")
        ip = int(whole) + int(frac) / 3.0
    else:
        ip = float(ip_raw)
    if ip <= 0:
        return None
    hr = float(stat.get("homeRuns", 0) or 0)
    bb = float(stat.get("baseOnBalls", 0) or 0)
    hbp = float(stat.get("hitByPitch", 0) or 0)
    k = float(stat.get("strikeOuts", 0) or 0)
    return (13 * hr + 3 * (bb + hbp) - 2 * k) / ip + FIP_CONSTANT


def _season_stats(team_id: int, season: int) -> dict:
    """{woba, fip} cumulative season totals for a team. Cached. NOTE: these are
    current totals, not as-of-date - a small forward-looking bias in the backtest's
    SOS (opponent-quality) term over a short window; win% is the as-of part."""
    if team_id in _SEASON:
        return _SEASON[team_id]
    out = {"woba": None, "fip": None}
    try:
        data = _get(f"teams/{team_id}/stats", stats="season",
                    group="hitting,pitching", season=season)
        for s in data.get("stats", []):
            grp = s.get("group", {}).get("displayName", "")
            splits = s.get("splits", [])
            if not splits:
                continue
            stat = splits[0].get("stat", {})
            if grp == "hitting":
                out["woba"] = _woba(stat)
            elif grp == "pitching":
                out["fip"] = _fip(stat)
    except Exception as exc:
        log.warning("team season stats load failed for %s: %s", team_id, exc)
    _SEASON[team_id] = out
    return out


def team_strength(team_id: int | None, season: int, as_of: str | None = None) -> dict:
    """
    {win_pct, woba, fip} for a team. win_pct is as of `as_of` (or current);
    woba/fip are season totals. Neutral defaults (0.5 / None) on any failure.
    """
    if not team_id:
        return {"win_pct": 0.5, "woba": None, "fip": None}
    stats = _season_stats(team_id, season)
    return {"win_pct": _winpct(season, as_of).get(team_id, 0.5),
            "woba": stats["woba"], "fip": stats["fip"]}
