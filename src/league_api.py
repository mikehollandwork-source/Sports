"""
Generic league schedule / results / team names, driven by the sport registry.

WHY GENERIC
nfl_api hardcodes one league. With WNBA now and NBA/NHL in October, copying it
per sport would mean four near-identical files drifting apart. This takes the
sport key and reads everything else from sports.py. nfl_api stays as it is - it
is verified and working, and rewriting it mid-flight to prove a point about
duplication is a worse trade than the duplication.

TEAM TABLES ARE BUILT FROM WHAT THE VENUES REPORT, not from memory. The WNBA
table below came out of league_probe: Kalshi's abbreviations paired against
Polymarket's outcome labels. Writing it from recall would have missed both 2026
expansion teams - Toronto Tempo and Portland Fire.

TWO THINGS THE PROBE CAUGHT for WNBA, both silent-failure shaped:

  1. Polymarket carries BOTH "Portland Fire" and "PortlandFire". An exact-match
     lookup silently drops every game labelled the second way, so the tables
     carry the no-space form explicitly.
  2. Kalshi lists two abbreviations - COO and SPN - that pair with no team on
     any other venue. They are deliberately NOT guessed at. Unmapped is safe
     (those markets are skipped); a wrong guess would attach real money to the
     wrong side.

Kalshi's WNBA tickers carry HHMM (KXWNBAGAME-26AUG10CHISEA-SEA has none, but
MLB-style time-bearing forms appear in the series), so kickoff comes from the
odds API with Polymarket as fallback - same order as nfl_api.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os

import requests

from . import apitime
from .sports import get as get_sport

log = logging.getLogger("league_api")

API = "https://api.the-odds-api.com/v4/sports"
TIMEOUT = 20
UA = {"User-Agent": "mlb-edge-finder (personal research)"}

# {sport_key: {kalshi_abbr: (name forms...)}} - first form is canonical.
# WNBA verified against league_probe output 2026-08-07.
TEAMS: dict[str, dict[str, tuple[str, ...]]] = {
    "wnba": {
        "ATL": ("Atlanta Dream",),
        "CHI": ("Chicago Sky",),
        "CONN": ("Connecticut Sun",),
        "DAL": ("Dallas Wings",),
        "GS": ("Golden State Valkyries",),
        "IND": ("Indiana Fever",),
        "LA": ("Los Angeles Sparks",),
        "LV": ("Las Vegas Aces",),
        "MIN": ("Minnesota Lynx",),
        "NY": ("New York Liberty",),
        # Polymarket emits this one both with and without the space.
        "PDX": ("Portland Fire", "PortlandFire"),
        "PHX": ("Phoenix Mercury",),
        "SEA": ("Seattle Storm",),
        "TOR": ("Toronto Tempo",),
        "WSH": ("Washington Mystics",),
    },
}

# Kalshi abbreviations seen in a series that match no known team. Left unmapped
# on purpose - a market we skip costs nothing, a market mapped to the wrong team
# costs a bet.
UNMAPPED: dict[str, tuple[str, ...]] = {"wnba": ("COO", "SPN")}


def _load_nfl() -> None:
    """NFL's 32 teams live in nfl_api, which predates this module. Referenced
    rather than copied - two hand-maintained copies of the same table drift, and
    a team that maps in one and not the other fails SILENTLY here: name_abbr
    returns None, _row drops the game, and the log simply stays empty.

    That is not hypothetical. Without this the generic logger mapped zero NFL
    teams and would have logged nothing all preseason while reporting success -
    the same shape of silent failure that left the WNBA log ungraded."""
    try:
        from . import nfl_api
    except Exception:
        return
    if getattr(nfl_api, "TEAMS", None):
        TEAMS.setdefault("nfl", dict(nfl_api.TEAMS))


_load_nfl()


def _key() -> str | None:
    return os.environ.get("THE_ODDS_API_KEY") or None


def _get(path: str, odds_key: str, **params):
    if not _key():
        log.warning("THE_ODDS_API_KEY not set - %s data unavailable", odds_key)
        return None
    try:
        with apitime.timed("oddsapi", path):
            r = requests.get(f"{API}/{odds_key}{path}",
                             params={"apiKey": _key(), **params},
                             timeout=TIMEOUT, headers=UA)
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        log.warning("odds api failed (%s %s): %s", odds_key, path, exc)
        return None


def _name2abbr(sport: str) -> dict:
    return {n.lower(): ab for ab, names in TEAMS.get(sport, {}).items()
            for n in names}


def name_abbr(sport: str, text: str) -> str | None:
    """Outcome label / team name -> Kalshi abbreviation, or None."""
    low = (text or "").strip().lower()
    if not 3 <= len(low) <= 40:
        return None
    table = _name2abbr(sport)
    if low in table:
        return table[low]
    for name, ab in table.items():
        nick = name.rsplit(" ", 1)[-1]
        if len(nick) >= 4 and low.endswith(nick):
            return ab
    return None


def _iso_ts(iso) -> int | None:
    try:
        return int(dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def schedule(sport: str, date: str) -> list[dict]:
    """Games on a YYYY-MM-DD date (by start time in UTC)."""
    sp = get_sport(sport)
    out = []
    for ev in _get("/events", sp.odds_key) or []:
        an, hn = ev.get("away_team"), ev.get("home_team")
        aa, ha = name_abbr(sport, str(an or "")), name_abbr(sport, str(hn or ""))
        if not (an and hn and aa and ha):
            continue
        if str(ev.get("commence_time") or "")[:10] != date:
            continue
        out.append({"game_id": ev.get("id"), "matchup": f"{an} @ {hn}",
                    "away": an, "home": hn, "away_abbr": aa, "home_abbr": ha,
                    "game_datetime": ev.get("commence_time"),
                    "start_ts": _iso_ts(ev.get("commence_time"))})
    return out


def results_for(sport: str, date: str) -> dict:
    """{game_id: {final, winner, away_score, home_score}} - mlb_api's shape."""
    sp = get_sport(sport)
    out: dict = {}
    for ev in _get("/scores", sp.odds_key, daysFrom=3) or []:
        if str(ev.get("commence_time") or "")[:10] != date:
            continue
        an, hn = ev.get("away_team"), ev.get("home_team")
        sc = {}
        for s in ev.get("scores") or []:
            try:
                sc[s.get("name")] = int(s.get("score"))
            except (TypeError, ValueError):
                continue
        a, h = sc.get(an), sc.get(hn)
        winner = None
        final = bool(ev.get("completed"))
        if final and a is not None and h is not None and a != h:
            winner = hn if h > a else an
        out[ev.get("id")] = {"final": final, "winner": winner,
                             "away_score": a, "home_score": h}
    return out


def pm_kickoffs(sport: str) -> dict:
    """{frozenset{abbr,abbr}: {start_ts, event_date, ended}} from Polymarket -
    the fallback for games the odds API has not listed. `startTime` is kickoff;
    `startDate` is market creation and must not be used."""
    from . import pm_books

    sp = get_sport(sport)
    out: dict = {}
    for off in (0, 100, 200):
        batch = pm_books._get(pm_books.GAMMA, tag_slug=sp.pm_tag,
                              closed="false", limit=100, offset=off)
        if not isinstance(batch, list) or not batch:
            break
        for ev in batch:
            pair = None
            for m in ev.get("markets") or []:
                outs = m.get("outcomes")
                if isinstance(outs, str):
                    try:
                        outs = json.loads(outs)
                    except ValueError:
                        continue
                if not outs or len(outs) != 2:
                    continue
                a1 = name_abbr(sport, str(outs[0]))
                a2 = name_abbr(sport, str(outs[1]))
                if a1 and a2 and a1 != a2:
                    pair = frozenset({a1, a2})
                    break
            ts = _iso_ts(ev.get("startTime"))
            if pair and ts is not None:
                out[pair] = {"start_ts": ts, "event_date": ev.get("eventDate"),
                             "ended": bool(ev.get("ended"))}
        if len(batch) < 100:
            break
    return out


def start_ts_for(sport: str, date: str, away_abbr: str, home_abbr: str) -> int | None:
    a, h = (away_abbr or "").upper(), (home_abbr or "").upper()
    for g in schedule(sport, date):
        if g["away_abbr"] == a and g["home_abbr"] == h:
            return g["start_ts"]
    hit = pm_kickoffs(sport).get(frozenset({a, h}))
    return hit["start_ts"] if hit else None
