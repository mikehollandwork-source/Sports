"""
Best 1+ HIT prop per play (user spec): look through the picked team's season
WINS - the hitter who most consistently records a hit in the games his team
wins is the prop. Quality-PA guard so it's always an everyday, top-of-the-order
type bat, never a bench player with a lucky small sample.

For each play:
  1. the team's season WINS (schedule endpoint, final games only)
  2. tonight's projected lineup (boxscore batting order / roster fallback)
  3. each hitter's season game log -> over the team-wins he played:
       hit_rate = wins with >=1 hit / wins played
     guarded by MIN_WINS_PLAYED and MIN_AVG_PA (quality at-bats)
  4. highest hit_rate wins the prop (avg PA breaks ties)

Returns {player, hit_rate, wins_played, avg_pa}; None when nothing qualifies.
All fetches fail soft; per-day caches keep the hourly loop cheap.
"""

from __future__ import annotations

import logging

from . import mlb_api

log = logging.getLogger("props")

MIN_WINS_PLAYED = 12   # a real season sample of team wins
MIN_AVG_PA = 3.2       # quality at-bats: everyday bats, effectively lineup top-6
MAX_LINEUP_BATS = 9

_WINS_CACHE: dict[tuple, set] = {}      # (team_id, date) -> {winning gamePks}
_LOG_CACHE: dict[tuple, list] = {}      # (player_id, season) -> gameLog splits


def _team_win_pks(team_id: int, date: str) -> set:
    key = (team_id, date)
    if key in _WINS_CACHE:
        return _WINS_CACHE[key]
    season = date[:4]
    wins: set = set()
    try:
        data = mlb_api._get("schedule", sportId=1, teamId=team_id,
                            startDate=f"{season}-03-20", endDate=date)
        for day in data.get("dates", []):
            for g in day.get("games", []):
                if g.get("status", {}).get("abstractGameState") != "Final":
                    continue
                for side in ("home", "away"):
                    t = g["teams"][side]
                    if t.get("team", {}).get("id") == team_id and t.get("isWinner"):
                        wins.add(g["gamePk"])
    except Exception as exc:
        log.warning("team wins fetch failed (%s): %s", team_id, exc)
    _WINS_CACHE[key] = wins
    return wins


def _game_log(player_id: int, season: int) -> list:
    key = (player_id, season)
    if key in _LOG_CACHE:
        return _LOG_CACHE[key]
    splits: list = []
    try:
        data = mlb_api._get(f"people/{player_id}/stats", stats="gameLog",
                            group="hitting", season=season)
        for s in (data.get("stats") or [{}])[0].get("splits", []) or []:
            splits.append(s)
    except Exception as exc:
        log.warning("game log fetch failed (%s): %s", player_id, exc)
    _LOG_CACHE[key] = splits
    return splits


def best_hit_prop(game_pk: int, team_id: int, date: str, home: bool) -> dict | None:
    """The picked team's most-consistent hitter-in-wins (see module doc)."""
    wins = _team_win_pks(team_id, date)
    if len(wins) < MIN_WINS_PLAYED:
        return None
    try:
        bats = mlb_api.lineup(game_pk, team_id, date, home)[:MAX_LINEUP_BATS]
    except Exception as exc:
        log.warning("lineup fetch failed (%s): %s", game_pk, exc)
        return None
    season = int(date[:4])
    best: dict | None = None
    for p in bats:
        played = with_hit = 0
        pa_total = 0.0
        for s in _game_log(p.player_id, season):
            if (s.get("game") or {}).get("gamePk") not in wins:
                continue
            st = s.get("stat") or {}
            try:
                pa = float(st.get("plateAppearances", 0) or 0)
                hits = float(st.get("hits", 0) or 0)
            except (TypeError, ValueError):
                continue
            if pa < 1:
                continue
            played += 1
            pa_total += pa
            if hits >= 1:
                with_hit += 1
        if played < MIN_WINS_PLAYED or (pa_total / played) < MIN_AVG_PA:
            continue
        rate = with_hit / played
        cand = {"player": p.name, "player_id": p.player_id,
                "hit_rate": round(rate * 100),
                "wins_played": played, "avg_pa": round(pa_total / played, 1)}
        if best is None or (rate, cand["avg_pa"]) > (best["hit_rate"] / 100, best["avg_pa"]):
            best = cand
    return best
