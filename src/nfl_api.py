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

SOURCE: THE ODDS API, not ESPN. ESPN's public API was the obvious choice and
returned nothing from a GitHub runner (nfl_probe, 2026-08-07) - it blocks cloud
IPs. The Odds API is already wired into these workflows via THE_ODDS_API_KEY,
already proven in prop_odds, and serves schedule (`commence_time`) and results
(`/scores`) from one authenticated source.

THE TEAM MAP IS A STATIC TABLE, VERIFIED BY PROBE. The Odds API returns full
team names, not abbreviations, so a mapping is unavoidable. A hand-typed table
is normally a silent-failure generator - one typo and that team's games quietly
never match - so nfl_probe checks it against the 32 abbreviations Kalshi
actually uses and fails loudly on any gap.

Mirrors mlb_api's shapes so downstream modules need no special-casing:
results_for(date) -> {game_id: {final, winner, away_score, home_score}} with
`winner` as the full display name, matching how mlb_api reports it.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import zoneinfo

import requests

from . import apitime

log = logging.getLogger("nfl_api")

API = "https://api.the-odds-api.com/v4/sports"
# Verified against /v4/sports (nfl_probe, 2026-08-07): the only NFL keys are
# `americanfootball_nfl` and a Super Bowl futures market. There is NO preseason
# key - The Odds API does not cover preseason at all, and regular-season events
# only appear once books price them. So in August this returns nothing, which is
# correct rather than broken: NFL is not graded until the September opener.
# Kickoff for any game the odds API has not listed comes from Polymarket, whose
# gamma events carry a start time and which already matches NFL games by team.
SPORT_KEYS = ("americanfootball_nfl",)
TIMEOUT = 20
EASTERN = zoneinfo.ZoneInfo("America/New_York")
UA = {"User-Agent": "mlb-edge-finder (personal research)"}


def _key() -> str | None:
    return os.environ.get("THE_ODDS_API_KEY") or None


def _get(path: str, sport: str, **params):
    if not _key():
        log.warning("THE_ODDS_API_KEY not set - NFL data unavailable")
        return None
    try:
        with apitime.timed("oddsapi", path):
            r = requests.get(f"{API}/{sport}{path}",
                             params={"apiKey": _key(), **params},
                             timeout=TIMEOUT, headers=UA)
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        log.warning("odds api fetch failed (%s %s %s): %s", sport, path, params, exc)
        return None


def sport_keys() -> list:
    """Every football sport key the API currently exposes - so a renamed or
    missing preseason key shows up as data rather than an empty schedule."""
    try:
        r = requests.get(API, params={"apiKey": _key()}, timeout=TIMEOUT, headers=UA)
        r.raise_for_status()
        return [s.get("key") for s in (r.json() or [])
                if "americanfootball" in str(s.get("key", ""))]
    except Exception as exc:
        log.warning("sport key list failed: %s", exc)
        return []


# The 32 NFL teams, keyed by the abbreviation Kalshi uses in its tickers.
# nfl_probe verifies this against Kalshi's live abbreviation set - a missing or
# misspelled entry would silently drop that team's games forever.
TEAMS: dict[str, tuple[str, ...]] = {
    "ARI": ("Arizona Cardinals",), "ATL": ("Atlanta Falcons",),
    "BAL": ("Baltimore Ravens",), "BUF": ("Buffalo Bills",),
    "CAR": ("Carolina Panthers",), "CHI": ("Chicago Bears",),
    "CIN": ("Cincinnati Bengals",), "CLE": ("Cleveland Browns",),
    "DAL": ("Dallas Cowboys",), "DEN": ("Denver Broncos",),
    "DET": ("Detroit Lions",), "GB": ("Green Bay Packers",),
    "HOU": ("Houston Texans",), "IND": ("Indianapolis Colts",),
    "JAC": ("Jacksonville Jaguars",), "KC": ("Kansas City Chiefs",),
    "LAC": ("Los Angeles Chargers",), "LAR": ("Los Angeles Rams",),
    "LV": ("Las Vegas Raiders",), "MIA": ("Miami Dolphins",),
    "MIN": ("Minnesota Vikings",), "NE": ("New England Patriots",),
    "NO": ("New Orleans Saints",), "NYG": ("New York Giants",),
    "NYJ": ("New York Jets",), "PHI": ("Philadelphia Eagles",),
    "PIT": ("Pittsburgh Steelers",), "SEA": ("Seattle Seahawks",),
    "SF": ("San Francisco 49ers",), "TB": ("Tampa Bay Buccaneers",),
    "TEN": ("Tennessee Titans",), "WAS": ("Washington Commanders",),
}

_NAME2ABBR = {n.lower(): ab for ab, names in TEAMS.items() for n in names}


def team_map() -> dict[str, str]:
    """{lowercased team name: abbr}."""
    return dict(_NAME2ABBR)


def name_abbr(text: str) -> str | None:
    """NFL counterpart to public_sources._name_abbr. Exact match, then an
    endswith-nickname match, length-capped so prose cannot hit."""
    low = (text or "").strip().lower()
    if not 3 <= len(low) <= 40:
        return None
    if low in _NAME2ABBR:
        return _NAME2ABBR[low]
    for name, ab in _NAME2ABBR.items():
        nick = name.rsplit(" ", 1)[-1]
        if len(nick) >= 4 and low.endswith(nick):
            return ab
    return None


def _iso_ts(iso) -> int | None:
    try:
        return int(dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def _upcoming() -> list:
    """Scheduled NFL events across regular season AND preseason keys."""
    out = []
    for sk in SPORT_KEYS:
        out.extend(_get("/events", sk) or [])
    return out


def _scores(days_from: int = 3) -> list:
    """Recent + live events with scores, both keys. days_from capped at 3."""
    out = []
    for sk in SPORT_KEYS:
        out.extend(_get("/scores", sk, daysFrom=max(1, min(3, days_from))) or [])
    return out


def _row(ev: dict) -> dict | None:
    an, hn = ev.get("away_team"), ev.get("home_team")
    aa, ha = name_abbr(str(an or "")), name_abbr(str(hn or ""))
    if not an or not hn or not aa or not ha:
        return None
    return {"game_id": ev.get("id"), "matchup": f"{an} @ {hn}",
            "away": an, "home": hn, "away_abbr": aa, "home_abbr": ha,
            "game_datetime": ev.get("commence_time"),
            "start_ts": _iso_ts(ev.get("commence_time"))}


def schedule(date: str) -> list[dict]:
    """Games on a YYYY-MM-DD date (by kickoff in UTC). [] on failure."""
    out = []
    for ev in _upcoming():
        r = _row(ev)
        if r and str(r["game_datetime"] or "")[:10] == date:
            out.append(r)
    return out


def results_for(date: str) -> dict:
    """{game_id: {final, winner, away_score, home_score}} - mlb_api's shape, so
    downstream graders need no special-casing. `winner` is the full team name."""
    out: dict = {}
    for ev in _scores():
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
        final = bool(ev.get("completed"))
        winner = None
        if final and a is not None and h is not None and a != h:
            winner = hn if h > a else an
        out[ev.get("id")] = {"final": final, "winner": winner,
                             "away_score": a, "home_score": h}
    return out


def pm_kickoffs(tag: str = "nfl") -> dict:
    """{frozenset{abbr, abbr}: {start_ts, event_date, ended}} from Polymarket.

    The odds API has no preseason coverage and lists regular-season games only
    once books price them, so gamma is the kickoff source for everything it
    cannot see. Verified field names (nfl_probe, 2026-08-07) on a real game
    event: `startTime` is kickoff, `eventDate` the local game date, `ended` /
    `finishedTimestamp` completion. NOT `startDate` - that is when the market
    was created, which on the sampled game was a month before kickoff.

    Keyed by an unordered pair: gamma's title ("Panthers vs. Cardinals") does
    not reliably say which side is home."""
    from . import pm_books

    out: dict = {}
    for off in (0, 100, 200):
        batch = pm_books._get(pm_books.GAMMA, tag_slug=tag, closed="false",
                              limit=100, offset=off)
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
                a1, a2 = name_abbr(str(outs[0])), name_abbr(str(outs[1]))
                if a1 and a2 and a1 != a2:
                    pair = frozenset({a1, a2})
                    break
            if not pair:
                continue                      # a futures market, not a game
            ts = _iso_ts(ev.get("startTime"))
            if ts is None:
                continue
            out[pair] = {"start_ts": ts, "event_date": ev.get("eventDate"),
                         "ended": bool(ev.get("ended"))}
        if len(batch) < 100:
            break
    return out


_PM_CACHE: dict | None = None


def start_ts_for(date: str, away_abbr: str, home_abbr: str) -> int | None:
    """Kickoff for one matchup - the thing Kalshi's NFL ticker omits. Tries the
    odds API first, then falls back to Polymarket."""
    global _PM_CACHE
    a, h = (away_abbr or "").upper(), (home_abbr or "").upper()
    for g in schedule(date):
        if g["away_abbr"] == a and g["home_abbr"] == h:
            return g["start_ts"]
    if _PM_CACHE is None:
        _PM_CACHE = pm_kickoffs()
    hit = _PM_CACHE.get(frozenset({a, h}))
    return hit["start_ts"] if hit else None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(EASTERN).date().isoformat()
    for g in schedule(date):
        print(f"  {g['game_id']}  {g['matchup']:48s} "
              f"{g['away_abbr']} @ {g['home_abbr']}  {g['game_datetime']}")


if __name__ == "__main__":
    main()
