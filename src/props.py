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
        # gameType="R,P" or the log stops at the end of the REGULAR SEASON.
        # Probed 2026-10-01: no gameType and gameType=R both returned 162 games
        # ending 09-27; P returned the 2 postseason games; R,P returned all 164.
        # Without this every form number freezes once October starts - Albies read
        # 0-for-2 on "the last game" when he had gone 1-for-4 two days later.
        data = mlb_api._get(f"people/{player_id}/stats", stats="gameLog",
                            group="hitting", season=season, gameType="R,P")
        for s in (data.get("stats") or [{}])[0].get("splits", []) or []:
            splits.append(s)
    except Exception as exc:
        log.warning("game log fetch failed (%s): %s", player_id, exc)
    _LOG_CACHE[key] = splits
    return splits


RECENT_GAMES = 5       # "hot" window, matching the board's own last-5 framing
SUPER_HOT = 15         # percentage points above his own season rate


def hit_in_wins_ranked(game_pk: int, team_id: int, date: str, home: bool,
                       exclude_pk: int | None = None,
                       opp_pitcher_id: int | None = None) -> list[dict]:
    """Tonight's lineup ranked by hit rate in the team's season WINS.

    Each entry also carries `all_rate` - the same hitter's hit rate across EVERY
    game he played, not just the wins. That second number is what makes the
    first one readable. `hit_rate` conditions on the outcome: a team that wins
    usually hit well, so every regular's rate rises inside wins, and the
    statistic partly measures "did the offence show up" - which is the thing
    that caused the win. A hitter at 89% in wins and 74% overall is largely
    telling you the team wins when he hits. One whose two numbers are CLOSE is
    the dependable bat, and `gap` is that difference.

    Each entry also carries `form` - his hit rate over his last RECENT_GAMES
    games minus his season rate, in percentage points - and `bvp` against
    tonight's opposing starter when `opp_pitcher_id` is given. `form` is derived
    from the same game log already being fetched, so it costs nothing and covers
    the whole lineup rather than the board's top-two hot and cold.

    exclude_pk drops one game from the season-wins sample - used by the backtest
    to reconstruct the pre-game prop without leaking the game being graded (live
    callers leave it None, since tonight's game isn't final yet anyway).
    """
    wins = _team_win_pks(team_id, date)
    if exclude_pk is not None:
        wins = wins - {exclude_pk}
    if len(wins) < MIN_WINS_PLAYED:
        return []
    try:
        bats = mlb_api.lineup(game_pk, team_id, date, home)[:MAX_LINEUP_BATS]
    except Exception as exc:
        log.warning("lineup fetch failed (%s): %s", game_pk, exc)
        return []
    season = int(date[:4])
    out: list[dict] = []
    for p in bats:
        played = with_hit = 0
        all_played = all_with_hit = 0
        pa_total = 0.0
        recent: list[tuple[str, bool]] = []      # (date, got a hit) for form
        for s in _game_log(p.player_id, season):
            st = s.get("stat") or {}
            try:
                pa = float(st.get("plateAppearances", 0) or 0)
                hits = float(st.get("hits", 0) or 0)
            except (TypeError, ValueError):
                continue
            if pa < 1:
                continue
            pk = (s.get("game") or {}).get("gamePk")
            if pk == exclude_pk:
                continue                  # never count the game being graded
            d = s.get("date") or ""
            if d and d >= date:
                continue                  # never let tonight or later inform form
            all_played += 1
            all_with_hit += 1 if hits >= 1 else 0
            recent.append((d, hits >= 1))
            if pk not in wins:
                continue
            played += 1
            pa_total += pa
            if hits >= 1:
                with_hit += 1
        if played < MIN_WINS_PLAYED or (pa_total / played) < MIN_AVG_PA:
            continue
        rate = with_hit / played
        all_rate = (all_with_hit / all_played) if all_played else None
        # form: his last-5 hit rate against his OWN season rate, so a 55% hitter
        # at 80% reads hot and an 80% hitter at 80% does not
        form = None
        if all_rate is not None and len(recent) >= RECENT_GAMES:
            recent.sort(key=lambda x: x[0])
            last = recent[-RECENT_GAMES:]
            form = round((sum(1 for _, h in last if h) / len(last) - all_rate) * 100)
        bvp = None
        if opp_pitcher_id:
            try:
                bvp = mlb_api.batter_vs_pitcher(p.player_id, opp_pitcher_id)
            except Exception as exc:
                log.warning("bvp failed (%s vs %s): %s", p.player_id,
                            opp_pitcher_id, exc)
        out.append({"player": p.name, "player_id": p.player_id,
                    "hit_rate": round(rate * 100),
                    "all_rate": round(all_rate * 100) if all_rate is not None else None,
                    "gap": (round((rate - all_rate) * 100)
                            if all_rate is not None else None),
                    "form": form, "super_hot": form is not None and form >= SUPER_HOT,
                    "bvp": bvp,
                    "wins_played": played, "games_played": all_played,
                    "avg_pa": round(pa_total / played, 1)})
    out.sort(key=lambda c: (c["hit_rate"], c["avg_pa"]), reverse=True)
    return out


def best_hit_prop(game_pk: int, team_id: int, date: str, home: bool,
                  exclude_pk: int | None = None) -> dict | None:
    """The picked team's most-consistent hitter-in-wins (see module doc).

    Kept as the single-best entry point the prop ledger and grader already use;
    the ranking and the all-games comparison live in hit_in_wins_ranked().
    """
    ranked = hit_in_wins_ranked(game_pk, team_id, date, home, exclude_pk)
    return ranked[0] if ranked else None
