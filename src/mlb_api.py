"""
Official MLB Stats API client (statsapi.mlb.com).

Free, public, no key required. Used for:
  - today's schedule + probable pitchers
  - per-player last-5-game logs (hitting)
  - probable pitcher last-5-start logs (pitching)

Docs are unofficial; field paths below are based on the public v1 API and may
need small adjustments after the first live run (see README).
"""

from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass, field

import requests

BASE = "https://statsapi.mlb.com/api/v1"
SPORT_ID = 1  # MLB
TIMEOUT = 20
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "mlb-edge-finder/1.0"})


def _get(path: str, **params) -> dict:
    """GET a v1 endpoint and return parsed JSON, raising on HTTP errors."""
    resp = SESSION.get(f"{BASE}/{path}", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


@dataclass
class Player:
    player_id: int
    name: str


@dataclass
class Team:
    team_id: int
    name: str
    abbreviation: str = ""
    probable_pitcher: Player | None = None
    # Filled in by the stats layer:
    hitter_ops_last5: float | None = None   # avg OPS of probable/roster hitters
    pitcher_era_last5: float | None = None
    pitcher_whip_last5: float | None = None


@dataclass
class Game:
    game_pk: int
    date: str
    home: Team
    away: Team
    venue: str = ""
    extra: dict = field(default_factory=dict)


def schedule_for(date: str) -> list[Game]:
    """Return the MLB games scheduled on `date` (YYYY-MM-DD)."""
    data = _get(
        "schedule",
        sportId=SPORT_ID,
        date=date,
        hydrate="probablePitcher,team",
    )
    games: list[Game] = []
    for day in data.get("dates", []):
        for g in day.get("games", []):
            home_raw = g["teams"]["home"]
            away_raw = g["teams"]["away"]
            games.append(
                Game(
                    game_pk=g["gamePk"],
                    date=date,
                    venue=g.get("venue", {}).get("name", ""),
                    home=_team_from_raw(home_raw),
                    away=_team_from_raw(away_raw),
                )
            )
    return games


def _team_from_raw(raw: dict) -> Team:
    t = raw["team"]
    pp = raw.get("probablePitcher")
    probable = Player(pp["id"], pp.get("fullName", "")) if pp else None
    return Team(
        team_id=t["id"],
        name=t.get("name", ""),
        abbreviation=t.get("abbreviation", ""),
        probable_pitcher=probable,
    )


def _season_for(date: str) -> int:
    return dt.date.fromisoformat(date).year


def roster_hitter_ids(team_id: int, date: str) -> list[Player]:
    """Active-roster position players for a team (used as the hitting sample)."""
    data = _get(f"teams/{team_id}/roster", rosterType="active", date=date)
    players: list[Player] = []
    for entry in data.get("roster", []):
        pos = entry.get("position", {}).get("type", "")
        if pos and pos != "Pitcher":
            players.append(Player(entry["person"]["id"], entry["person"].get("fullName", "")))
    return players


def _last_n_gamelog(player_id: int, group: str, season: int, n: int = 5) -> list[dict]:
    """Return the most recent `n` game-log split rows for a player."""
    data = _get(
        f"people/{player_id}/stats",
        stats="gameLog",
        group=group,
        season=season,
    )
    splits: list[dict] = []
    for s in data.get("stats", []):
        splits.extend(s.get("splits", []))
    # game logs come oldest->newest; take the last n
    return splits[-n:]


def hitter_ops_last5(player_id: int, season: int) -> float | None:
    """Average OPS across a hitter's last 5 games (None if no data)."""
    rows = _last_n_gamelog(player_id, "hitting", season, 5)
    ops_vals = []
    for r in rows:
        stat = r.get("stat", {})
        ops = stat.get("ops")
        if ops not in (None, "-", ".---"):
            try:
                ops_vals.append(float(ops))
            except ValueError:
                continue
    if not ops_vals:
        return None
    return sum(ops_vals) / len(ops_vals)


def pitcher_last5(player_id: int, season: int) -> tuple[float | None, float | None]:
    """Return (ERA, WHIP) aggregated over a pitcher's last 5 outings."""
    rows = _last_n_gamelog(player_id, "pitching", season, 5)
    er = ip = bb = h = 0.0
    found = False
    for r in rows:
        stat = r.get("stat", {})
        try:
            er += float(stat.get("earnedRuns", 0))
            ip += _ip_to_float(stat.get("inningsPitched", "0"))
            bb += float(stat.get("baseOnBalls", 0))
            h += float(stat.get("hits", 0))
            found = True
        except (ValueError, TypeError):
            continue
    if not found or ip == 0:
        return None, None
    era = (er * 9.0) / ip
    whip = (bb + h) / ip
    return round(era, 3), round(whip, 3)


def _ip_to_float(ip: str | float) -> float:
    """Convert MLB innings-pitched notation (e.g. '5.2' = 5 and 2/3) to float."""
    s = str(ip)
    if "." in s:
        whole, frac = s.split(".")
        return int(whole) + int(frac) / 3.0
    return float(s)


def enrich_with_stats(game: Game, date: str, polite_delay: float = 0.2) -> Game:
    """Populate last-5 hitting/pitching ratings for both teams of a game."""
    season = _season_for(date)
    for team in (game.home, game.away):
        # Hitting: average OPS over the roster's position players (last 5 each).
        hitters = roster_hitter_ids(team.team_id, date)
        ops_vals = []
        for p in hitters:
            v = hitter_ops_last5(p.player_id, season)
            if v is not None:
                ops_vals.append(v)
            time.sleep(polite_delay)
        team.hitter_ops_last5 = round(sum(ops_vals) / len(ops_vals), 4) if ops_vals else None

        # Pitching: probable starter's last 5 outings.
        if team.probable_pitcher:
            era, whip = pitcher_last5(team.probable_pitcher.player_id, season)
            team.pitcher_era_last5 = era
            team.pitcher_whip_last5 = whip
        time.sleep(polite_delay)
    return game
