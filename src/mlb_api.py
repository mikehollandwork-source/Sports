"""
Official MLB Stats API client (statsapi.mlb.com).

Free, public, no key required. Provides everything the advantage metric needs,
all from the last 5 games:

  - today's schedule + probable pitchers (with throwing hand)
  - each team's projected lineup (boxscore battingOrder, falling back to roster)
  - per-hitter last-5 counting stats (for wOBA / ISO / discipline / speed),
    park-neutralized by the parks actually played in
  - probable starter's last-5 FIP inputs
  - bullpen's last-5 FIP inputs (relievers aggregated)

The v1 API is undocumented; field paths below are best-effort and may need a
small tweak after the first live run (this code can't be tested from the build
sandbox, where the API is firewalled). Network/parse failures degrade soft.
"""

from __future__ import annotations

import datetime as dt
import logging
import time
from dataclasses import dataclass, field

import requests

from .park_factors import factor_for

log = logging.getLogger("mlb_api")

BASE = "https://statsapi.mlb.com/api/v1"
SPORT_ID = 1
TIMEOUT = 20
POLITE_DELAY = 0.1
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "mlb-edge-finder/1.0"})


def _get(path: str, **params) -> dict:
    resp = SESSION.get(f"{BASE}/{path}", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    time.sleep(POLITE_DELAY)
    return resp.json()


# --- data models --------------------------------------------------------------
@dataclass
class Player:
    player_id: int
    name: str
    hand: str = ""        # pitcher throws / batter bats: "L"/"R"/"S"
    pa: int = 0           # last-5 plate appearances (hitters)


@dataclass
class Team:
    team_id: int
    name: str
    abbreviation: str = ""
    probable_pitcher: Player | None = None
    # Filled by enrich_with_stats():
    offense: dict = field(default_factory=dict)   # last-5 rate line (see analysis)
    starter_fip_last5: float | None = None
    bullpen_fip_last5: float | None = None
    platoon_factor: float = 1.0
    runs_last5: list = field(default_factory=list)  # runs scored, last 5 completed games


@dataclass
class Game:
    game_pk: int
    date: str
    home: Team
    away: Team
    venue: str = ""
    park_factor: float = 1.0


# --- schedule -----------------------------------------------------------------
def schedule_for(date: str) -> list[Game]:
    data = _get("schedule", sportId=SPORT_ID, date=date, hydrate="probablePitcher,team")
    games: list[Game] = []
    for day in data.get("dates", []):
        for g in day.get("games", []):
            home = _team_from_raw(g["teams"]["home"])
            away = _team_from_raw(g["teams"]["away"])
            games.append(
                Game(
                    game_pk=g["gamePk"],
                    date=date,
                    venue=g.get("venue", {}).get("name", ""),
                    home=home,
                    away=away,
                    park_factor=factor_for(home.name),
                )
            )
    return games


def _team_from_raw(raw: dict) -> Team:
    t = raw["team"]
    pp = raw.get("probablePitcher")
    probable = Player(pp["id"], pp.get("fullName", "")) if pp else None
    return Team(team_id=t["id"], name=t.get("name", ""), abbreviation=t.get("abbreviation", ""),
                probable_pitcher=probable)


def _season_for(date: str) -> int:
    return dt.date.fromisoformat(date).year


# --- game logs ----------------------------------------------------------------
def _last_n_gamelog(player_id: int, group: str, season: int, n: int = 5) -> list[dict]:
    data = _get(f"people/{player_id}/stats", stats="gameLog", group=group, season=season)
    splits: list[dict] = []
    for s in data.get("stats", []):
        splits.extend(s.get("splits", []))
    return splits[-n:]  # logs are oldest->newest


def _row_park_factor(team_name: str, split: dict) -> float:
    """Park factor for the game this split represents (best-effort)."""
    try:
        if split.get("isHome", True):
            return factor_for(team_name)
        opp = split.get("opponent", {}).get("name", "")
        return factor_for(opp)
    except Exception:
        return 1.0


def _ip_to_float(ip) -> float:
    s = str(ip)
    if "." in s:
        whole, frac = s.split(".")
        return int(whole) + int(frac) / 3.0
    return float(s or 0)


# --- hitting: last-5 counting stats, park-neutralized -------------------------
HIT_FIELDS = {
    "ab": "atBats", "h": "hits", "2b": "doubles", "3b": "triples", "hr": "homeRuns",
    "bb": "baseOnBalls", "so": "strikeOuts", "hbp": "hitByPitch", "sf": "sacFlies",
    "sb": "stolenBases", "pa": "plateAppearances", "tb": "totalBases",
}


def hitter_last5(player_id: int, team_name: str, season: int) -> dict:
    """Sum a hitter's last-5 counting stats + PA-weighted park factor."""
    rows = _last_n_gamelog(player_id, "hitting", season, 5)
    acc = {k: 0.0 for k in HIT_FIELDS}
    park_pa = pf_weight = 0.0
    for r in rows:
        stat = r.get("stat", {})
        pa = float(stat.get("plateAppearances", 0) or 0)
        for k, src in HIT_FIELDS.items():
            acc[k] += float(stat.get(src, 0) or 0)
        pf = _row_park_factor(team_name, r)
        park_pa += pf * pa
        pf_weight += pa
    acc["park_factor"] = (park_pa / pf_weight) if pf_weight else 1.0
    return acc


# --- pitching: last-5 FIP inputs ----------------------------------------------
def pitcher_fip_last5(player_id: int, season: int) -> float | None:
    rows = _last_n_gamelog(player_id, "pitching", season, 5)
    hr = bb = hbp = k = 0.0
    ip = 0.0
    for r in rows:
        stat = r.get("stat", {})
        hr += float(stat.get("homeRuns", 0) or 0)
        bb += float(stat.get("baseOnBalls", 0) or 0)
        hbp += float(stat.get("hitByPitch", 0) or 0)
        k += float(stat.get("strikeOuts", 0) or 0)
        ip += _ip_to_float(stat.get("inningsPitched", 0))
    if ip == 0:
        return None
    from .analysis import FIP_CONSTANT
    return round((13 * hr + 3 * (bb + hbp) - 2 * k) / ip + FIP_CONSTANT, 3)


# --- roster / lineup / handedness ---------------------------------------------
def _people(ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    data = _get("people", personIds=",".join(str(i) for i in ids))
    return {p["id"]: p for p in data.get("people", [])}


def probable_hands(game: Game) -> None:
    """Fill each probable pitcher's throwing hand."""
    ids = [t.probable_pitcher.player_id for t in (game.home, game.away) if t.probable_pitcher]
    people = _people(ids)
    for t in (game.home, game.away):
        pp = t.probable_pitcher
        if pp and pp.player_id in people:
            pp.hand = people[pp.player_id].get("pitchHand", {}).get("code", "")


def lineup(game_pk: int, team_id: int, date: str, home: bool) -> list[Player]:
    """Projected lineup: boxscore battingOrder if posted, else roster hitters."""
    try:
        box = SESSION.get(
            f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore", timeout=TIMEOUT
        ).json()
        side = "home" if home else "away"
        order = box["teams"][side].get("battingOrder", [])
        if order:
            people = _people(list(order))
            return [
                Player(pid, people.get(pid, {}).get("fullName", ""),
                       hand=people.get(pid, {}).get("batSide", {}).get("code", ""))
                for pid in order
            ]
    except Exception as exc:
        log.warning("boxscore lineup unavailable for %s (%s); using roster", game_pk, exc)

    data = _get(f"teams/{team_id}/roster", rosterType="active", date=date)
    ids = [
        e["person"]["id"]
        for e in data.get("roster", [])
        if e.get("position", {}).get("type", "") not in ("Pitcher", "")
    ]
    people = _people(ids)
    return [
        Player(pid, people.get(pid, {}).get("fullName", ""),
               hand=people.get(pid, {}).get("batSide", {}).get("code", ""))
        for pid in ids
    ]


def last5_runs_scored(team_id: int, date: str, lookback_days: int = 21) -> list[int]:
    """Runs the team scored in its last 5 completed regular-season games before `date`."""
    start = (dt.date.fromisoformat(date) - dt.timedelta(days=lookback_days)).isoformat()
    data = _get("schedule", sportId=SPORT_ID, teamId=team_id,
                startDate=start, endDate=date, gameType="R")
    games: list[tuple[str, int]] = []
    for day in data.get("dates", []):
        for g in day.get("games", []):
            if g.get("status", {}).get("abstractGameState") != "Final":
                continue
            home, away = g["teams"]["home"], g["teams"]["away"]
            if home["team"]["id"] == team_id:
                rs = home.get("score")
            elif away["team"]["id"] == team_id:
                rs = away.get("score")
            else:
                continue
            if rs is not None:
                games.append((g.get("gameDate", ""), int(rs)))
    games.sort()
    return [rs for _, rs in games[-5:]]


def reliever_ids(team_id: int, date: str, starter_id: int | None) -> list[int]:
    """Active-roster pitchers other than today's probable starter (the bullpen)."""
    data = _get(f"teams/{team_id}/roster", rosterType="active", date=date)
    out = []
    for e in data.get("roster", []):
        if e.get("position", {}).get("type", "") == "Pitcher":
            pid = e["person"]["id"]
            if pid != starter_id:
                out.append(pid)
    return out


# --- orchestration ------------------------------------------------------------
def enrich_with_stats(game: Game, date: str) -> Game:
    """Populate last-5 offense + starter/bullpen FIP + handedness for both teams."""
    season = _season_for(date)
    probable_hands(game)

    for team, is_home in ((game.home, True), (game.away, False)):
        # --- offense: aggregate the lineup's last-5 counting stats ---
        hitters = lineup(game.game_pk, team.team_id, date, is_home)
        agg = {k: 0.0 for k in HIT_FIELDS}
        park_num = park_den = 0.0
        bats = []  # (bat_hand, pa) for platoon factor
        for h in hitters:
            try:
                line = hitter_last5(h.player_id, team.name, season)
            except Exception as exc:
                log.warning("hitter %s last-5 failed: %s", h.player_id, exc)
                continue
            pa = line["pa"]
            for k in HIT_FIELDS:
                agg[k] += line[k]
            park_num += line["park_factor"] * pa
            park_den += pa
            bats.append((h.hand, pa))
        agg["park_factor"] = (park_num / park_den) if park_den else 1.0
        team.offense = agg
        team.offense["bats"] = bats  # consumed by analysis.platoon_factor

        # --- pitching: starter FIP + bullpen FIP (last 5) ---
        if team.probable_pitcher:
            try:
                team.starter_fip_last5 = pitcher_fip_last5(team.probable_pitcher.player_id, season)
            except Exception as exc:
                log.warning("starter FIP failed for %s: %s", team.name, exc)

        try:
            starter_id = team.probable_pitcher.player_id if team.probable_pitcher else None
            rel = reliever_ids(team.team_id, date, starter_id)
            hr = bb = hbp = k = ip = 0.0
            for pid in rel:
                rows = _last_n_gamelog(pid, "pitching", season, 5)
                for r in rows:
                    s = r.get("stat", {})
                    hr += float(s.get("homeRuns", 0) or 0)
                    bb += float(s.get("baseOnBalls", 0) or 0)
                    hbp += float(s.get("hitByPitch", 0) or 0)
                    k += float(s.get("strikeOuts", 0) or 0)
                    ip += _ip_to_float(s.get("inningsPitched", 0))
            if ip > 0:
                from .analysis import FIP_CONSTANT
                team.bullpen_fip_last5 = round(
                    (13 * hr + 3 * (bb + hbp) - 2 * k) / ip + FIP_CONSTANT, 3
                )
        except Exception as exc:
            log.warning("bullpen FIP failed for %s: %s", team.name, exc)

        # --- runs scored in last 5 games (for the win-condition back-test) ---
        try:
            team.runs_last5 = last5_runs_scored(team.team_id, date)
        except Exception as exc:
            log.warning("last-5 runs failed for %s: %s", team.name, exc)

    return game
