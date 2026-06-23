"""
Combine public sentiment with last-5-game stats and flag the target case:

    The team that does NOT have the public majority, but DOES have the
    statistical advantage over the last 5 games.

Statistical-advantage metric (documented, easy to tweak):

    team_score = offense_rating + pitching_rating
      offense_rating = avg OPS of the team's hitters over their last 5 games
                       (higher is better)
      pitching_rating = probable starter's last-5 form, mapped so higher = better:
                       (LEAGUE_ERA - era)/LEAGUE_ERA + (LEAGUE_WHIP - whip)/LEAGUE_WHIP

    The team with the higher team_score has the statistical advantage.
    Missing data -> that component contributes 0 (and is noted in the output).
"""

from __future__ import annotations

from .mlb_api import Game, Team

LEAGUE_ERA = 4.20   # rough MLB baselines for normalization
LEAGUE_WHIP = 1.30


def _pitching_rating(team: Team) -> float:
    era = team.pitcher_era_last5
    whip = team.pitcher_whip_last5
    rating = 0.0
    if era is not None:
        rating += (LEAGUE_ERA - era) / LEAGUE_ERA
    if whip is not None:
        rating += (LEAGUE_WHIP - whip) / LEAGUE_WHIP
    return rating


def _offense_rating(team: Team) -> float:
    return team.hitter_ops_last5 or 0.0


def team_score(team: Team) -> float:
    return round(_offense_rating(team) + _pitching_rating(team), 4)


def statistical_favorite(game: Game) -> tuple[Team, float, float]:
    """Return (advantaged_team, home_score, away_score)."""
    hs = team_score(game.home)
    as_ = team_score(game.away)
    winner = game.home if hs >= as_ else game.away
    return winner, hs, as_


def public_majority(
    game: Game,
    consensus: dict[str, dict[str, float]],
    forum_counts: dict[str, int],
) -> tuple[Team | None, dict]:
    """
    Determine the public-majority team from BOTH signals.

    Returns (majority_team_or_None, detail_dict). When the two signals disagree
    the detail records both; the majority_team falls back to consensus, then
    forum, when only one is available.
    """
    detail: dict = {"consensus": None, "forum": None, "agree": None}

    # --- consensus signal ---
    cons_team = None
    for key, pcts in consensus.items():
        names = list(pcts.keys())
        if _matches(game, names):
            top = max(pcts, key=pcts.get)
            cons_team = _resolve(game, top)
            detail["consensus"] = {"pick": top, "pcts": pcts}
            break

    # --- forum signal ---
    forum_team = None
    h, a = game.home.name, game.away.name
    hc, ac = forum_counts.get(h, 0), forum_counts.get(a, 0)
    if hc or ac:
        forum_team = game.home if hc >= ac else game.away
        detail["forum"] = {"pick": forum_team.name, "home": hc, "away": ac}

    if cons_team and forum_team:
        detail["agree"] = cons_team.team_id == forum_team.team_id

    majority = cons_team or forum_team
    return majority, detail


def evaluate_game(
    game: Game,
    consensus: dict[str, dict[str, float]],
    forum_counts: dict[str, int],
) -> dict:
    """Full per-game evaluation. `flagged` is the headline result."""
    adv_team, hs, as_ = statistical_favorite(game)
    majority, majority_detail = public_majority(game, consensus, forum_counts)

    # The target case: stats favor the team the public is NOT on.
    flagged = bool(majority) and adv_team.team_id != majority.team_id

    return {
        "game_pk": game.game_pk,
        "matchup": f"{game.away.name} @ {game.home.name}",
        "venue": game.venue,
        "statistical_advantage": {
            "team": adv_team.name,
            "home_score": hs,
            "away_score": as_,
            "home": _team_stats(game.home),
            "away": _team_stats(game.away),
        },
        "public_majority": {
            "team": majority.name if majority else None,
            "detail": majority_detail,
        },
        "flagged": flagged,
        "pick": adv_team.name if flagged else None,
    }


def _team_stats(team: Team) -> dict:
    return {
        "name": team.name,
        "probable_pitcher": team.probable_pitcher.name if team.probable_pitcher else None,
        "hitter_ops_last5": team.hitter_ops_last5,
        "pitcher_era_last5": team.pitcher_era_last5,
        "pitcher_whip_last5": team.pitcher_whip_last5,
        "score": team_score(team),
    }


def _matches(game: Game, names: list[str]) -> bool:
    joined = " ".join(names).lower()
    return _name_hit(game.home, joined) and _name_hit(game.away, joined)


def _name_hit(team: Team, blob: str) -> bool:
    nick = team.name.lower().split()[-1] if team.name else ""
    return bool(nick) and nick in blob


def _resolve(game: Game, label: str) -> Team:
    """Map a covers team label back to the home/away Team object."""
    low = label.lower()
    home_nick = game.home.name.lower().split()[-1] if game.home.name else ""
    return game.home if home_nick and home_nick in low else game.away
