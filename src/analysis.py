"""
Advantage metric + the public-vs-stats decision.

Everything is built from the LAST 5 GAMES and expressed as a league-relative
index (0 = league average, +0.10 = ~10% above average) so the pieces add up
coherently:

    team_score = offense_index + pitching_index          (higher = better)

OFFENSE (park-neutralized, platoon-adjusted last-5 line):
    offense_index = W_WOBA  * wOBA-vs-league
                  + W_ISO   * ISO-vs-league          (power)
                  + W_DISC  * (BB% - K%)-vs-league    (plate discipline)
                  + W_SPEED * SB-rate-vs-league       (baserunning)
    then tilted by a platoon factor for the lineup's bat hands vs the
    opposing starter's throwing hand.
    wOBA is the backbone; ISO/discipline/speed add dimensions wOBA blurs.

PITCHING (FIP, lower is better -> positive index):
    combined_FIP   = W_SP * starter_FIP + W_BP * bullpen_FIP   (last 5)
    pitching_index = (LEAGUE_FIP - combined_FIP) / LEAGUE_FIP

The advantaged team has the higher team_score. We then flag games where that
team is NOT the public's majority side. All knobs live here.
"""

from __future__ import annotations

from .mlb_api import Game, Team

# --- tunable constants (the whole formula lives here) -------------------------
FIP_CONSTANT = 3.10      # maps FIP onto the ERA scale
LEAGUE_FIP = 4.10
LEAGUE_WOBA = 0.320
LEAGUE_ISO = 0.165
LEAGUE_BB = 0.085        # BB%
LEAGUE_K = 0.225         # K%
LEAGUE_SB_RATE = 0.018   # SB per PA

# offense component weights (sum ~1.0; wOBA is the backbone)
W_WOBA, W_ISO, W_DISC, W_SPEED = 0.55, 0.20, 0.15, 0.10
# pitching weights: starters throw ~55% of innings, bullpen ~45%
W_SP, W_BP = 0.55, 0.45
# league-average platoon swing applied per handedness matchup
PLATOON = 0.03

# wOBA linear weights (approx; intentional walks not split out)
WOBA_W = {"bb": 0.69, "hbp": 0.72, "1b": 0.89, "2b": 1.27, "3b": 1.62, "hr": 2.10}


# --- offense ------------------------------------------------------------------
def offense_line(agg: dict) -> dict:
    """Turn aggregated last-5 counting stats into a park-neutral rate line."""
    ab = agg.get("ab", 0.0)
    pa = agg.get("pa", 0.0)
    if ab <= 0 or pa <= 0:
        return {}
    h, hr = agg["h"], agg["hr"]
    b2, b3 = agg["2b"], agg["3b"]
    bb, hbp, sf, so, sb, tb = agg["bb"], agg["hbp"], agg["sf"], agg["so"], agg["sb"], agg["tb"]
    singles = h - b2 - b3 - hr
    pf = agg.get("park_factor", 1.0) or 1.0

    avg = h / ab
    obp = (h + bb + hbp) / (ab + bb + hbp + sf) if (ab + bb + hbp + sf) else 0.0
    slg = tb / ab
    woba_den = ab + bb + sf + hbp
    woba = (
        WOBA_W["bb"] * bb + WOBA_W["hbp"] * hbp + WOBA_W["1b"] * singles
        + WOBA_W["2b"] * b2 + WOBA_W["3b"] * b3 + WOBA_W["hr"] * hr
    ) / woba_den if woba_den else 0.0
    iso = slg - avg

    # park-neutralize the run-production rates (not discipline/speed)
    return {
        "avg": round(avg, 3), "obp": round(obp, 3), "slg": round(slg, 3),
        "ops": round(obp + slg, 3), "iso": round(iso, 3), "woba": round(woba, 3),
        "bb_pct": round(bb / pa, 3), "k_pct": round(so / pa, 3),
        "sb_rate": round(sb / pa, 4), "pa": int(pa),
        "park_factor": round(pf, 3),
        "woba_neutral": round(woba / pf, 3), "iso_neutral": round(iso / pf, 3),
    }


def offense_index(team: Team) -> float:
    line = offense_line(team.offense)
    if not line:
        return 0.0
    woba_idx = line["woba_neutral"] / LEAGUE_WOBA - 1.0
    iso_idx = line["iso_neutral"] / LEAGUE_ISO - 1.0
    disc_idx = line["bb_pct"] / LEAGUE_BB - line["k_pct"] / LEAGUE_K  # ~0 centered
    speed_idx = line["sb_rate"] / LEAGUE_SB_RATE - 1.0
    raw = W_WOBA * woba_idx + W_ISO * iso_idx + W_DISC * disc_idx + W_SPEED * speed_idx
    # tilt by platoon: treat (1+raw) as a run-rate and scale it
    return round((1.0 + raw) * team.platoon_factor - 1.0, 4)


def platoon_factor(bats: list, opp_hand: str) -> float:
    """PA-weighted lineup platoon multiplier vs the opposing starter's hand."""
    if opp_hand not in ("L", "R") or not bats:
        return 1.0
    num = den = 0.0
    for hand, pa in bats:
        pa = pa or 0
        if hand == "S":
            mult = 1.0 + PLATOON           # switch hitters always get the platoon edge
        elif hand in ("L", "R"):
            mult = 1.0 + PLATOON if hand != opp_hand else 1.0 - PLATOON
        else:
            mult = 1.0
        num += mult * pa
        den += pa
    return round(num / den, 4) if den else 1.0


# --- pitching -----------------------------------------------------------------
def pitching_index(team: Team) -> float:
    sp, bp = team.starter_fip_last5, team.bullpen_fip_last5
    if sp is not None and bp is not None:
        combined = W_SP * sp + W_BP * bp
    elif sp is not None:
        combined = sp
    elif bp is not None:
        combined = bp
    else:
        return 0.0
    return round((LEAGUE_FIP - combined) / LEAGUE_FIP, 4)


def team_score(team: Team) -> float:
    return round(offense_index(team) + pitching_index(team), 4)


# --- decision -----------------------------------------------------------------
def statistical_favorite(game: Game) -> tuple[Team, float, float]:
    hs, as_ = team_score(game.home), team_score(game.away)
    winner = game.home if hs >= as_ else game.away
    return winner, hs, as_


def public_majority(game, consensus, forum_counts) -> tuple[Team | None, dict]:
    detail = {"consensus": None, "forum": None, "agree": None}

    cons_team = None
    for _, pcts in consensus.items():
        names = list(pcts.keys())
        if _matches(game, names):
            top = max(pcts, key=pcts.get)
            cons_team = _resolve(game, top)
            detail["consensus"] = {"pick": top, "pcts": pcts}
            break

    forum_team = None
    hc, ac = forum_counts.get(game.home.name, 0), forum_counts.get(game.away.name, 0)
    if hc or ac:
        forum_team = game.home if hc >= ac else game.away
        detail["forum"] = {"pick": forum_team.name, "home": hc, "away": ac}

    if cons_team and forum_team:
        detail["agree"] = cons_team.team_id == forum_team.team_id

    return (cons_team or forum_team), detail


def evaluate_game(game: Game, consensus: dict, forum_counts: dict) -> dict:
    # platoon depends on the matchup, so set it before scoring
    home_opp = game.away.probable_pitcher.hand if game.away.probable_pitcher else ""
    away_opp = game.home.probable_pitcher.hand if game.home.probable_pitcher else ""
    game.home.platoon_factor = platoon_factor(game.home.offense.get("bats", []), home_opp)
    game.away.platoon_factor = platoon_factor(game.away.offense.get("bats", []), away_opp)

    adv_team, hs, as_ = statistical_favorite(game)
    majority, majority_detail = public_majority(game, consensus, forum_counts)
    flagged = bool(majority) and adv_team.team_id != majority.team_id

    return {
        "game_pk": game.game_pk,
        "matchup": f"{game.away.name} @ {game.home.name}",
        "venue": game.venue,
        "park_factor": game.park_factor,
        "statistical_advantage": {
            "team": adv_team.name,
            "home_score": hs, "away_score": as_,
            "home": _team_stats(game.home), "away": _team_stats(game.away),
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
        "starter_hand": team.probable_pitcher.hand if team.probable_pitcher else None,
        "offense": offense_line(team.offense),
        "platoon_factor": team.platoon_factor,
        "starter_fip_last5": team.starter_fip_last5,
        "bullpen_fip_last5": team.bullpen_fip_last5,
        "offense_index": offense_index(team),
        "pitching_index": pitching_index(team),
        "score": team_score(team),
    }


def _matches(game: Game, names: list[str]) -> bool:
    blob = " ".join(names).lower()
    return _name_hit(game.home, blob) and _name_hit(game.away, blob)


def _name_hit(team: Team, blob: str) -> bool:
    nick = team.name.lower().split()[-1] if team.name else ""
    return bool(nick) and nick in blob


def _resolve(game: Game, label: str) -> Team:
    low = label.lower()
    home_nick = game.home.name.lower().split()[-1] if game.home.name else ""
    return game.home if home_nick and home_nick in low else game.away
