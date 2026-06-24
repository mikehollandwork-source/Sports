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
from . import strength

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
    starter_ip_last5: float = 0.0   # innings behind the starter FIP (sample size)
    bullpen_ip_last5: float = 0.0   # innings behind the bullpen FIP (sample size)
    platoon_factor: float = 1.0
    games_last5: list = field(default_factory=list)  # per-game results + opp strength
    sos: dict = field(default_factory=dict)          # avg opp strength faced (see analysis)


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


def results_for(date: str) -> dict[int, dict]:
    """Final scores for a date, keyed by game_pk: {final, winner, home, away,
    home_score, away_score}. `winner` is the winning team name ("" if tie/n.a.)."""
    data = _get("schedule", sportId=SPORT_ID, date=date, hydrate="team,linescore")
    out: dict[int, dict] = {}
    for day in data.get("dates", []):
        for g in day.get("games", []):
            home, away = g["teams"]["home"], g["teams"]["away"]
            final = g.get("status", {}).get("abstractGameState") == "Final"
            hs, as_ = home.get("score"), away.get("score")
            winner = ""
            if home.get("isWinner"):
                winner = home["team"].get("name", "")
            elif away.get("isWinner"):
                winner = away["team"].get("name", "")
            elif final and hs is not None and as_ is not None:
                winner = (home if hs > as_ else away)["team"].get("name", "")
            out[g["gamePk"]] = {
                "final": final, "winner": winner,
                "home": home["team"].get("name", ""), "away": away["team"].get("name", ""),
                "home_score": hs, "away_score": as_,
            }
    return out


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


def _opp_strength(split: dict, season: int) -> dict:
    """Season strength of the opponent in a game-log split (neutral on miss)."""
    opp = split.get("opponent", {})
    return strength.team_strength(opp.get("id"), season)


# --- hitting: last-5 counting stats, park-neutralized -------------------------
HIT_FIELDS = {
    "ab": "atBats", "h": "hits", "2b": "doubles", "3b": "triples", "hr": "homeRuns",
    "bb": "baseOnBalls", "so": "strikeOuts", "hbp": "hitByPitch", "sf": "sacFlies",
    "sb": "stolenBases", "pa": "plateAppearances", "tb": "totalBases",
}


def hitter_last5(player_id: int, team_name: str, season: int) -> dict:
    """Sum a hitter's last-5 counting stats + PA-weighted park factor and the
    PA-weighted strength (FIP, win%) of the pitching staffs faced."""
    rows = _last_n_gamelog(player_id, "hitting", season, 5)
    acc = {k: 0.0 for k in HIT_FIELDS}
    park_pa = pf_weight = 0.0
    opp_fip_pa = opp_fip_w = opp_win_pa = 0.0
    for r in rows:
        stat = r.get("stat", {})
        pa = float(stat.get("plateAppearances", 0) or 0)
        for k, src in HIT_FIELDS.items():
            acc[k] += float(stat.get(src, 0) or 0)
        pf = _row_park_factor(team_name, r)
        park_pa += pf * pa
        pf_weight += pa
        s = _opp_strength(r, season)
        opp_win_pa += s["win_pct"] * pa
        if s["fip"] is not None:
            opp_fip_pa += s["fip"] * pa
            opp_fip_w += pa
    acc["park_factor"] = (park_pa / pf_weight) if pf_weight else 1.0
    acc["opp_fip"] = (opp_fip_pa / opp_fip_w) if opp_fip_w else None
    acc["opp_win"] = (opp_win_pa / pf_weight) if pf_weight else 0.5
    acc["weight_pa"] = pf_weight
    return acc


# --- pitching: last-5 FIP inputs ----------------------------------------------
def _accumulate_pitching(rows: list[dict], season: int, acc: dict) -> None:
    """Add FIP component sums + IP-weighted opponent-offense strength from rows."""
    for r in rows:
        stat = r.get("stat", {})
        ip = _ip_to_float(stat.get("inningsPitched", 0))
        acc["hr"] += float(stat.get("homeRuns", 0) or 0)
        acc["bb"] += float(stat.get("baseOnBalls", 0) or 0)
        acc["hbp"] += float(stat.get("hitByPitch", 0) or 0)
        acc["k"] += float(stat.get("strikeOuts", 0) or 0)
        acc["ip"] += ip
        s = _opp_strength(r, season)
        acc["opp_win_ip"] += s["win_pct"] * ip
        if s["woba"] is not None:
            acc["opp_woba_ip"] += s["woba"] * ip
            acc["opp_woba_w"] += ip


def _fip_from_acc(acc: dict) -> dict:
    """Turn accumulated pitching sums into FIP + opponent-offense averages + IP."""
    if acc["ip"] <= 0:
        return {"fip": None, "opp_woba": None, "opp_win": 0.5, "ip": 0.0}
    from .analysis import FIP_CONSTANT
    fip = (13 * acc["hr"] + 3 * (acc["bb"] + acc["hbp"]) - 2 * acc["k"]) / acc["ip"] + FIP_CONSTANT
    return {
        "fip": round(fip, 3),
        "opp_woba": (acc["opp_woba_ip"] / acc["opp_woba_w"]) if acc["opp_woba_w"] else None,
        "opp_win": (acc["opp_win_ip"] / acc["ip"]) if acc["ip"] else 0.5,
        "ip": round(acc["ip"], 2),
    }


def _new_pitch_acc() -> dict:
    return {"hr": 0.0, "bb": 0.0, "hbp": 0.0, "k": 0.0, "ip": 0.0,
            "opp_woba_ip": 0.0, "opp_woba_w": 0.0, "opp_win_ip": 0.0}


def pitcher_last5(player_id: int, season: int) -> dict:
    """Starter's last-5 FIP + IP-weighted opponent-offense strength faced."""
    acc = _new_pitch_acc()
    _accumulate_pitching(_last_n_gamelog(player_id, "pitching", season, 5), season, acc)
    return _fip_from_acc(acc)


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


def team_last5_gamelog(team_id: int, season: int) -> list[dict]:
    """
    Last 5 completed games as per-game dicts with runs/hits scored & allowed and
    the opponent's season strength (for the SOS-adjusted win-condition back-test).

    Team-level hitting game-log gives runs/hits scored; pitching gives runs/hits
    allowed; the two are aligned by date.
    """
    data = _get(f"teams/{team_id}/stats", stats="gameLog",
                group="hitting,pitching", season=season)
    hit_splits: list[dict] = []
    pit_by_date: dict[str, dict] = {}
    for s in data.get("stats", []):
        grp = s.get("group", {}).get("displayName", "")
        for sp in s.get("splits", []):
            if grp == "hitting":
                hit_splits.append(sp)
            elif grp == "pitching":
                pit_by_date[sp.get("date", "")] = sp

    out: list[dict] = []
    for sp in hit_splits[-5:]:
        hs = sp.get("stat", {})
        date = sp.get("date", "")
        opp = sp.get("opponent", {})
        ps = pit_by_date.get(date, {}).get("stat", {})
        strg = strength.team_strength(opp.get("id"), season)
        out.append({
            "date": date,
            "opponent": opp.get("name", ""),
            "runs_scored": int(hs.get("runs", 0) or 0),
            "hits": int(hs.get("hits", 0) or 0),
            "runs_allowed": int(ps.get("runs", 0) or 0),
            "hits_allowed": int(ps.get("hits", 0) or 0),
            "opp_fip": strg["fip"],
            "opp_woba": strg["woba"],
            "opp_win": strg["win_pct"],
        })
    return out


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
        sos: dict = {}

        # --- offense: aggregate the lineup's last-5 counting stats ---
        hitters = lineup(game.game_pk, team.team_id, date, is_home)
        agg = {k: 0.0 for k in HIT_FIELDS}
        park_num = park_den = 0.0
        opp_fip_num = opp_fip_w = opp_win_num = 0.0
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
            opp_win_num += line["opp_win"] * pa
            if line["opp_fip"] is not None:
                opp_fip_num += line["opp_fip"] * pa
                opp_fip_w += pa
            bats.append((h.hand, pa))
        agg["park_factor"] = (park_num / park_den) if park_den else 1.0
        team.offense = agg
        team.offense["bats"] = bats  # consumed by analysis.platoon_factor
        sos["bat_opp_fip"] = (opp_fip_num / opp_fip_w) if opp_fip_w else None
        sos["bat_opp_win"] = (opp_win_num / park_den) if park_den else 0.5

        # --- pitching: starter FIP + bullpen FIP (last 5), with opp offense ---
        if team.probable_pitcher:
            try:
                sp = pitcher_last5(team.probable_pitcher.player_id, season)
                team.starter_fip_last5 = sp["fip"]
                team.starter_ip_last5 = sp["ip"]
                sos["sp_opp_woba"], sos["sp_opp_win"] = sp["opp_woba"], sp["opp_win"]
            except Exception as exc:
                log.warning("starter FIP failed for %s: %s", team.name, exc)

        try:
            starter_id = team.probable_pitcher.player_id if team.probable_pitcher else None
            acc = _new_pitch_acc()
            for pid in reliever_ids(team.team_id, date, starter_id):
                _accumulate_pitching(_last_n_gamelog(pid, "pitching", season, 5), season, acc)
            bp = _fip_from_acc(acc)
            team.bullpen_fip_last5 = bp["fip"]
            team.bullpen_ip_last5 = bp["ip"]
            sos["bp_opp_woba"], sos["bp_opp_win"] = bp["opp_woba"], bp["opp_win"]
        except Exception as exc:
            log.warning("bullpen FIP failed for %s: %s", team.name, exc)

        team.sos = sos

        # --- last 5 games (for the SOS-adjusted win-condition back-test) ---
        try:
            team.games_last5 = team_last5_gamelog(team.team_id, season)
        except Exception as exc:
            log.warning("last-5 game log failed for %s: %s", team.name, exc)

    return game
