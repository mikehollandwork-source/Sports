"""
NFL schedule, results and team names - the pieces MLB gets from statsapi.

WHY THIS EXISTS
Two gaps blocked NFL entirely, both found by sport_probe:

  1. Kalshi's NFL tickers carry a DATE but no time
     (KXNFLGAME-26AUG15DALSEA-SEA vs MLB's KXMLBGAME-26AUG092020HOUSD-SD), so
     kickoff has to come from a schedule. Everything that truncates data "before
     first pitch" needs it.
  2. `_name_abbr` in public_sources is built from an MLB nickname table, so no
     NFL team name resolves to an abbreviation anywhere in the codebase.

ESPN's public site API covers both, needs no key, and returns schedule and
results from one endpoint.

THE TEAM MAP IS FETCHED, NOT TYPED. Hand-writing 32 nickname->abbr pairs is a
silent-failure generator - one typo and that team's games quietly never match,
which is precisely the class of bug that has cost the most time here. ESPN
publishes the mapping, so it is read from source and cached.

Mirrors mlb_api's shapes so downstream modules need no special-casing:
results_for(date) -> {game_id: {final, winner, away_score, home_score}} with
`winner` as the full display name, matching how mlb_api reports it.
"""

from __future__ import annotations

import datetime as dt
import logging
import zoneinfo

import requests

from . import apitime

log = logging.getLogger("nfl_api")

BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
TIMEOUT = 20
EASTERN = zoneinfo.ZoneInfo("America/New_York")
UA = {"User-Agent": "mlb-edge-finder (personal research)"}


def _get(path: str, **params):
    try:
        with apitime.timed("espn", path):
            r = requests.get(f"{BASE}{path}", params=params, timeout=TIMEOUT,
                             headers=UA)
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        log.warning("espn fetch failed (%s %s): %s", path, params, exc)
        return None


_TEAMS: dict[str, str] | None = None


def team_map() -> dict[str, str]:
    """{lowercased name fragment: abbr} built from ESPN's own team list.

    Several keys per team - full name, nickname, location - so whichever form a
    venue happens to use still resolves."""
    global _TEAMS
    if _TEAMS is not None:
        return _TEAMS
    out: dict[str, str] = {}
    data = _get("/teams") or {}
    try:
        groups = data["sports"][0]["leagues"][0]["teams"]
    except (KeyError, IndexError, TypeError):
        groups = []
    for g in groups:
        t = (g or {}).get("team") or {}
        ab = (t.get("abbreviation") or "").upper()
        if not ab:
            continue
        for form in (t.get("displayName"), t.get("shortDisplayName"),
                     t.get("name"), t.get("nickname"), t.get("location")):
            if form and len(str(form)) >= 3:
                out[str(form).strip().lower()] = ab
    _TEAMS = out
    log.info("espn: %d NFL team name forms -> %d teams",
             len(out), len(set(out.values())))
    return out


def name_abbr(text: str) -> str | None:
    """NFL counterpart to public_sources._name_abbr. Exact match first, then an
    endswith-nickname match, length-capped so prose cannot hit."""
    low = (text or "").strip().lower()
    if not 3 <= len(low) <= 40:
        return None
    tm = team_map()
    if low in tm:
        return tm[low]
    for form, ab in tm.items():
        if len(form) >= 4 and low.endswith(form):
            return ab
    return None


def _iso_ts(iso) -> int | None:
    try:
        return int(dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def _events(date: str) -> list:
    """Raw ESPN events for a YYYY-MM-DD date."""
    data = _get("/scoreboard", dates=date.replace("-", "")) or {}
    return data.get("events") or []


def schedule(date: str) -> list[dict]:
    """[{game_id, matchup, away, home, away_abbr, home_abbr, start_ts,
    game_datetime}] for the date. [] on failure."""
    out = []
    for ev in _events(date):
        try:
            comp = (ev.get("competitions") or [{}])[0]
            sides = comp.get("competitors") or []
            if len(sides) != 2:
                continue
            home = next(s for s in sides if s.get("homeAway") == "home")
            away = next(s for s in sides if s.get("homeAway") == "away")
            ht, at = home.get("team") or {}, away.get("team") or {}
            hn, an = ht.get("displayName"), at.get("displayName")
            if not hn or not an:
                continue
            out.append({
                "game_id": ev.get("id"),
                "matchup": f"{an} @ {hn}",
                "away": an, "home": hn,
                "away_abbr": (at.get("abbreviation") or "").upper(),
                "home_abbr": (ht.get("abbreviation") or "").upper(),
                "game_datetime": ev.get("date"),
                "start_ts": _iso_ts(ev.get("date")),
            })
        except (StopIteration, AttributeError, TypeError):
            continue
    return out


def results_for(date: str) -> dict:
    """{game_id: {final, winner, away_score, home_score}} - mlb_api's shape, so
    downstream graders need no special-casing. `winner` is the display name."""
    out: dict = {}
    for ev in _events(date):
        try:
            comp = (ev.get("competitions") or [{}])[0]
            sides = comp.get("competitors") or []
            if len(sides) != 2:
                continue
            home = next(s for s in sides if s.get("homeAway") == "home")
            away = next(s for s in sides if s.get("homeAway") == "away")
            state = (((ev.get("status") or {}).get("type") or {})
                     .get("state") or "").lower()
            final = state == "post"
            hs = int(home.get("score")) if str(home.get("score", "")).isdigit() else None
            as_ = int(away.get("score")) if str(away.get("score", "")).isdigit() else None
            winner = None
            if final and hs is not None and as_ is not None and hs != as_:
                w = home if hs > as_ else away
                winner = (w.get("team") or {}).get("displayName")
            out[ev.get("id")] = {"final": final, "winner": winner,
                                 "home_score": hs, "away_score": as_}
        except (StopIteration, AttributeError, TypeError, ValueError):
            continue
    return out


def start_ts_for(date: str, away_abbr: str, home_abbr: str) -> int | None:
    """Kickoff for one matchup - the thing Kalshi's NFL ticker omits."""
    a, h = (away_abbr or "").upper(), (home_abbr or "").upper()
    for g in schedule(date):
        if g["away_abbr"] == a and g["home_abbr"] == h:
            return g["start_ts"]
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(EASTERN).date().isoformat()
    for g in schedule(date):
        print(f"  {g['game_id']}  {g['matchup']:48s} "
              f"{g['away_abbr']} @ {g['home_abbr']}  {g['game_datetime']}")


if __name__ == "__main__":
    main()
