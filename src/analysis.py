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

import math

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

# strength-of-schedule: blend stat-based opponent quality with opponent win%,
# clamped so one cupcake/murderers'-row stretch can't dominate.
W_SOS_STAT = 0.70   # weight on opponent FIP (vs hitters) / wOBA (vs pitchers)
W_SOS_WIN = 0.30    # weight on opponent win%
LEAGUE_WINPCT = 0.500
SOS_CLAMP = (0.80, 1.25)

# A game is only picked when the advantage team also met the FULL win condition
# (scored its target AND held the opponent under its ceiling, SOS-adjusted) in at
# least this many of its last 5 games.
WC_PICK_MIN = 3

# Small-sample guard for last-5 FIP: a 2-IP spot start with two homers posts an
# absurd FIP that would otherwise dominate the pitching index. Regress each FIP
# toward the league mean by innings pitched: weight = ip / (ip + FIP_PRIOR_IP),
# so ~one start's worth of innings counts as a league-average prior. Tunable.
FIP_PRIOR_IP = 9.0

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


def _clamp(x: float) -> float:
    return max(SOS_CLAMP[0], min(SOS_CLAMP[1], x))


def opp_pitching_factor(opp_fip: float | None, opp_win: float | None) -> float:
    """>1 when the bats faced tough pitching (low FIP / strong opponents),
    so their production is credited more."""
    fip_idx = (LEAGUE_FIP - opp_fip) / LEAGUE_FIP if opp_fip is not None else 0.0
    win_idx = 2.0 * ((opp_win if opp_win is not None else LEAGUE_WINPCT) - LEAGUE_WINPCT)
    return _clamp(1.0 + W_SOS_STAT * fip_idx + W_SOS_WIN * win_idx)


def opp_offense_factor(opp_woba: float | None, opp_win: float | None) -> float:
    """>1 when the arms faced strong offenses (high wOBA / strong opponents),
    so suppressing them is credited more."""
    woba_idx = (opp_woba / LEAGUE_WOBA - 1.0) if opp_woba is not None else 0.0
    win_idx = 2.0 * ((opp_win if opp_win is not None else LEAGUE_WINPCT) - LEAGUE_WINPCT)
    return _clamp(1.0 + W_SOS_STAT * woba_idx + W_SOS_WIN * win_idx)


def offense_index(team: Team) -> float:
    line = offense_line(team.offense)
    if not line:
        return 0.0
    # strength-of-schedule: scale run production by the pitching the bats faced
    sos = opp_pitching_factor(team.sos.get("bat_opp_fip"), team.sos.get("bat_opp_win"))
    woba_idx = line["woba_neutral"] * sos / LEAGUE_WOBA - 1.0
    iso_idx = line["iso_neutral"] * sos / LEAGUE_ISO - 1.0
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
def _shrink_fip(fip: float | None, ip: float) -> float | None:
    """Regress a small-sample FIP toward the league mean by innings pitched, so a
    tiny noisy sample can't blow up the index."""
    if fip is None or ip <= 0:
        return fip
    w = ip / (ip + FIP_PRIOR_IP)
    return w * fip + (1.0 - w) * LEAGUE_FIP


def _adjusted_fip(fip: float | None, ip: float, opp_woba, opp_win) -> float | None:
    """Shrink a FIP for sample size, then SOS-adjust by the offense faced
    (tougher offense -> lower/better)."""
    fip = _shrink_fip(fip, ip)
    if fip is None:
        return None
    return fip / opp_offense_factor(opp_woba, opp_win)


def combined_fip(team: Team) -> float | None:
    """Starter+bullpen FIP, each sample-shrunk then SOS-adjusted for offenses faced."""
    sp = _adjusted_fip(team.starter_fip_last5, team.starter_ip_last5,
                       team.sos.get("sp_opp_woba"), team.sos.get("sp_opp_win"))
    bp = _adjusted_fip(team.bullpen_fip_last5, team.bullpen_ip_last5,
                       team.sos.get("bp_opp_woba"), team.sos.get("bp_opp_win"))
    if sp is not None and bp is not None:
        return W_SP * sp + W_BP * bp
    if sp is not None:
        return sp
    if bp is not None:
        return bp
    return None


def pitching_index(team: Team) -> float:
    combined = combined_fip(team)
    if combined is None:
        return 0.0
    return round((LEAGUE_FIP - combined) / LEAGUE_FIP, 4)


def team_score(team: Team) -> float:
    return round(offense_index(team) + pitching_index(team), 4)


# --- win condition: multi-part target + SOS-adjusted last-5 back-test ----------
def _rpg(games: list) -> float:
    return sum(g["runs_scored"] for g in games) / len(games)


def win_condition(team: Team, opp: Team) -> dict | None:
    """
    What `team` must do to beat `opp`, plus how often it did each over its own
    last 5 games — with every past game re-rated by the opponent it came against.

    Bars (derived from this matchup):
      runs_to_win   = floor(opp runs/g * team_FIP/leagueFIP) + 1   (must outscore)
      runs_to_allow = floor(team runs/g * opp_FIP/leagueFIP)       (must hold under)

    Back-test (each of the team's last 5 games, SOS-adjusted):
      adj_scored  = runs_scored  * opp_pitching_factor   (vs tough arms counts more)
      adj_allowed = runs_allowed / opp_offense_factor    (vs tough bats counts more)
      scored_target / held_under_ceiling / complete (both) / actually_won / out_hit
    """
    if not team.games_last5 or not opp.games_last5:
        return None
    team_rpg, opp_rpg = _rpg(team.games_last5), _rpg(opp.games_last5)
    team_fip = combined_fip(team) or LEAGUE_FIP
    opp_fip = combined_fip(opp) or LEAGUE_FIP

    exp_opp_runs = opp_rpg * (team_fip / LEAGUE_FIP)
    exp_own_runs = team_rpg * (opp_fip / LEAGUE_FIP)
    runs_to_win = math.floor(exp_opp_runs) + 1
    runs_to_allow = max(1, math.floor(exp_own_runs))

    scored = prevent = complete = won = outhit = 0
    per_game = []
    for g in team.games_last5:
        f_pit = opp_pitching_factor(g.get("opp_fip"), g.get("opp_win"))
        f_off = opp_offense_factor(g.get("opp_woba"), g.get("opp_win"))
        adj_scored = g["runs_scored"] * f_pit
        adj_allowed = g["runs_allowed"] / f_off
        s = adj_scored >= runs_to_win
        p = adj_allowed <= runs_to_allow
        w = g["runs_scored"] > g["runs_allowed"]
        oh = g["hits"] > g["hits_allowed"]
        scored += s; prevent += p; complete += (s and p); won += w; outhit += oh
        per_game.append({
            "date": g.get("date", ""), "opponent": g.get("opponent", ""),
            "scored": g["runs_scored"], "allowed": g["runs_allowed"],
            "hits": g["hits"], "hits_allowed": g["hits_allowed"],
            "adj_scored": round(adj_scored, 2), "adj_allowed": round(adj_allowed, 2),
            "opp_win_pct": round(g.get("opp_win", 0.5), 3),
        })
    n = len(team.games_last5)
    return {
        "runs_to_win": runs_to_win,
        "runs_to_allow": runs_to_allow,
        "expected_opponent_runs": round(exp_opp_runs, 2),
        "expected_own_runs": round(exp_own_runs, 2),
        "games": n,
        "back_test": {
            "scored_target": scored,
            "held_under_ceiling": prevent,
            "complete_win_condition": complete,
            "actually_won": won,
            "out_hit": outhit,
        },
        "avg_opp_win_pct_faced": round(sum(g.get("opp_win", 0.5) for g in team.games_last5) / n, 3),
        "per_game": per_game,
    }


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

    wc_home = win_condition(game.home, game.away)
    wc_away = win_condition(game.away, game.home)

    # The pick fires only when all three line up on the SAME (advantage) team:
    #   1. it holds the last-5 statistical advantage  (it's adv_team by definition)
    #   2. the public majority on covers is NOT on it (the public-vs-stats edge)
    #   3. it met the full win condition in >= 3 of its last 5 games
    public_vs_stats_edge = bool(majority) and adv_team.team_id != majority.team_id
    adv_wc = wc_home if adv_team.team_id == game.home.team_id else wc_away
    wc_hits = adv_wc["back_test"]["complete_win_condition"] if adv_wc else 0
    win_condition_met = wc_hits >= WC_PICK_MIN
    flagged = public_vs_stats_edge and win_condition_met

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
        "win_condition": {
            "home": wc_home,
            "away": wc_away,
        },
        "pick_criteria": {
            "public_vs_stats_edge": public_vs_stats_edge,
            "win_condition_met": win_condition_met,
            "complete_win_condition_hits": wc_hits,
            "threshold": WC_PICK_MIN,
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
        "starter_ip_last5": team.starter_ip_last5,
        "bullpen_fip_last5": team.bullpen_fip_last5,
        "bullpen_ip_last5": team.bullpen_ip_last5,
        "combined_fip_sos_adj": round(combined_fip(team), 3) if combined_fip(team) is not None else None,
        "strength_of_schedule": {
            "bat_opp_pitching_factor": round(
                opp_pitching_factor(team.sos.get("bat_opp_fip"), team.sos.get("bat_opp_win")), 3),
            "arm_opp_offense_factor": round(
                opp_offense_factor(team.sos.get("sp_opp_woba"), team.sos.get("sp_opp_win")), 3),
            "raw": team.sos,
        },
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
