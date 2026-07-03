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
# Season anchor for the offense rates. The POINT of the offense index is current
# form ("who's better at the moment"), so last-5 keeps the majority; the season
# line only sands the worst 5-game noise off (~190 team PA is a tiny sample).
# The graded-game audit showed the offense/ISO gaps separate winners from losers,
# so a steadier estimate of them should sharpen the margin.
OFF_SEASON_WEIGHT = 0.40
# pitching weights: starters throw ~55% of innings, bullpen ~45%
W_SP, W_BP = 0.55, 0.45
# The probable starter's season FIP is the single biggest single-game lever
# (calibrated: the better starter's team wins ~55%). Blend it with the noisier
# last-5 team-starter FIP - season is the stable anchor, last-5 catches recent
# form. Falls back to last-5 only when the season sample is too thin.
SEASON_SP_WEIGHT = 0.60
# league-average platoon swing applied per handedness matchup
PLATOON = 0.03

# strength-of-schedule: blend stat-based opponent quality with opponent win%,
# clamped so one cupcake/murderers'-row stretch can't dominate.
W_SOS_STAT = 0.70   # weight on opponent FIP (vs hitters) / wOBA (vs pitchers)
W_SOS_WIN = 0.30    # weight on opponent win%
LEAGUE_WINPCT = 0.500
SOS_CLAMP = (0.80, 1.25)

# Public side: the forum mention tally is weighted HIGHER than covers consensus.
# Each signal becomes a "lean toward the home team" in [-1, 1]; the weighted
# blend's sign picks the public-majority side. Raise PUBLIC_W_FORUM toward 1.0 to
# make the forum the sole voice; lower it to let consensus matter more.
PUBLIC_W_FORUM = 0.75   # forum votes are few, so each weighs more (user call)
PUBLIC_W_CONSENSUS = 0.35
PUBLIC_W_SOBETS = 0.35   # Scores & Odds bet% — an independent book number, weighted
                         # like covers consensus (the blend normalizes by weights present)

# Batter-vs-pitcher (blended read: exact career BvP shrunk toward vs-hand OPS):
#   below BVP_FLOOR the OPS gap is noise - not shown, no effect.
#   at/above it, the gap nudges the stat edge, capped at a home-field-sized bump
#   (calibration: BvP is ~50% overall but suggestive at big gaps - so only big,
#   robust gaps get a small vote; they can tilt a close lean, not manufacture one).
BVP_FLOOR = 0.05
BVP_TILT_CAP = 0.10
BVP_PEN_SHARE = 0.35   # FALLBACK pen share when a starter has no projected innings;
                       # normally the split is innings-projected per side (see
                       # statistical_favorite: opposing starter's season IP/start / 9)
PEN_BVP_MIN_PA = 100   # career PA behind the pen number before it joins the tilt
PROJ_IP_CLAMP = (3.0, 7.5)   # sane bounds on a projected start

# Weather x power: factors into EVERY open-air / retractable game (a fixed dome
# has no weather). The relative tilt scales continuously with how far conditions
# sit from a neutral ~70F/calm baseline AND with the lineups' power (ISO) gap -
# warm/windy air carries and helps the higher-power side; cold air suppresses
# power and helps the contact side. Capped below home field. (User-directed to
# factor into every game; the hot/windy split was the only piece calibrated -
# 486 games, power team 57% hot/windy vs 52% mild - the continuous sizing extends
# it, kept conservative and capped.)
WX_NEUTRAL_TEMP = 70    # deg F where the ball carries roughly neutrally
WX_TEMP_PER10 = 0.35    # "carry" units per 10F above/below neutral (signed)
WX_WIND_CALM = 8        # mph; wind above this adds carry/variance
WX_WIND_PER_MPH = 0.05  # carry units per mph above calm
WX_ISO_FLOOR = 0.010    # blended-ISO gap below this = no side to tilt toward
WX_GAP_SCALE = 3.0      # tilt = clamp(carry * iso_gap * scale, +/- cap)
WX_TILT_CAP = 0.08      # stays below home field (0.10)

# Play taxonomy (from the 06-26..07-01 graded-lean autopsy). Count the five winner
# signals - margin, favorite, line toward, consistency, BvP not against:
#   PICK = >= PICK_MIN_SIGNALS hits with at least one of margin/line/consistency
#          (the >=2 tier went 62% +5.66u, stacking to 77% at >=3 and 89% at >=4;
#          favorite+BvP alone graded 8-10 so that pair only makes a lean).
#   COIN FLIP = the old LOCK profile (line toward the opponent + public not
#          against them, bet the opponent) - back-tested to a coin flip (2-4),
#          so it's its own separately-graded category.
#   LEAN = exactly 1 hit (or the demoted favorite+BvP pair).
#   FADE = everything else (the Vegas special): bet against the unanimous
#          money% side; no clean money read = listed, never booked.
PICK_MIN_SIGNALS = 2
LEAN_STRONG_MARGIN = 0.30    # stat-edge margin signal (64% at/above vs 48% below)
LEAN_MIN_CONSISTENCY = 3     # consistency signal: advantage team >=3/5 (73%)
# Consistency also tilts the MARGIN itself (user call): the side that hit its
# SOS-adjusted win condition more often over the last 5 gets a small team_score
# bump per game of difference (max 5 * 0.04 = 0.20, comparable to the BvP cap).
CONS_MARGIN_W = 0.04
# Umpire x strikeouts (feeds the same matchup layer as BvP): a big-zone HP ump
# (K/gm well above league, from output/ump_tendencies_<season>.json built by
# src/umpire.py) hurts the strikeout-prone lineup more, so the margin tilts
# toward the lower-K side. The ump is only posted near first pitch, so this
# fires at the pre-game refresh; unknown ump / no table / thin sample = no tilt.
UMP_MIN_GAMES = 12    # ump needs this many games behind the tendency
UMP_K_EXTRA = 0.7     # Ks/game above league that counts as a big zone
UMP_KGAP_FLOOR = 0.015  # blended lineup K% gap below this = no meaningful edge
UMP_TILT_SCALE = 2.0    # tilt = min(scale * K% gap, cap)
UMP_TILT_CAP = 0.06

# Public-margin gate (106-game backtest of avg public % vs outcomes): a MILD
# public lean (50-70%) is the sharp side - it wins 56-60% and picks made INTO it
# went 3-5 (38%) / all stat sides into it 12-19 (-7.52u). A HEAVY lean
# (>= PUBLIC_HEAVY %) is the fadeable public - its side wins ~43% and stat sides
# against it went 4-1 (+3.45u). So a pick facing a mild public lean drops to a
# lean; facing a heavy one it stands.
PUBLIC_HEAVY = 70

# Pick decision: a hard gate of THREE must-haves (calibrated against a season of
# results - see src/wc_calibrate.py & src/edge_calibrate.py):
#   1. public fade    - the statistical favorite is the side the public is fading
#   2. stat edge      - the favorite's team_score margin >= EDGE_THRESHOLD, the
#                       level where the edge actually predicts winners (~62% at
#                       >=0.40; below it the favorite is a coin flip)
#   3. line in favor  - the moneyline moved toward our side (applied in main).
# `confidence` is a DISPLAY-ONLY strength = blend of the stat edge + public fade.
# The old "win condition" calibrated to ~0 predictive lift, so it no longer votes -
# it's renamed "consistency" and kept on the board as context only.
W_EDGE, W_FADE = 0.55, 0.45   # confidence display blend (sum 1)
EDGE_FULL = 0.40       # team_score margin that counts as a full-strength stat edge
EDGE_THRESHOLD = 0.40  # calibrated bar: the favorite only wins (~62%) at >= this
# Home field is a real, season-calibrated edge (home teams win ~53%) that the
# last-5 stat indices miss - add it to the home side's team_score. ~0.10 in
# team_score units = the ~3% win-prob bump under the 0.40->62% mapping. (Splitting
# the stats by venue added ~nothing, so we use a flat bump, not home/road splits.)
HOME_FIELD = 0.10

# Line-movement gate (implied-probability shift of OUR side, open->current):
#   < LINE_CONFIRM_MIN : noise / too small to mean anything (does not confirm)
#   LINE_CONFIRM_MIN..  : confirms the fade; "strong" once it clears LINE_STRONG
#   >= LINE_BIG         : suspiciously large - usually a pitcher change / news, not
#                         value, so we DON'T auto-confirm; flag it for a manual look.
LINE_CONFIRM_MIN = 0.02   # ~10c on the moneyline; below this is market noise
LINE_STRONG = 0.05        # a clearly strong sharp move
LINE_BIG = 0.08           # ~30c+; treat as news, verify before trusting


def _apply_tuning() -> None:
    """Override the decision params from output/tuning.json (written by the
    bankroll auto-tuner). DISABLED for now (user request) - the auto-tuner is
    off, so the defaults above always stand."""
    return
    import json
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "output", "tuning.json")
    try:
        with open(path) as f:
            params = json.load(f).get("params", {})
    except (OSError, ValueError):
        return
    g = globals()
    for k in ("EDGE_THRESHOLD", "EDGE_FULL", "W_EDGE", "W_FADE"):
        v = params.get(k)
        if isinstance(v, (int, float)):
            g[k] = float(v)


_apply_tuning()

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


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


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


def _blend_offense_lines(last5: dict, season: dict) -> dict:
    """Blend the last-5 rate line with the season rate line (form-forward:
    last-5 gets 1-OFF_SEASON_WEIGHT). Falls back to whichever exists."""
    if not season:
        return last5
    if not last5:
        return season
    keys = ("woba_neutral", "iso_neutral", "bb_pct", "k_pct", "sb_rate")
    return {k: (1 - OFF_SEASON_WEIGHT) * last5[k] + OFF_SEASON_WEIGHT * season[k]
            for k in keys}


def offense_index(team: Team) -> float:
    line = _blend_offense_lines(offense_line(team.offense),
                                offense_line(team.season_offense))
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
    """Starter+bullpen FIP, each sample-shrunk then SOS-adjusted for offenses faced.
    The starter side blends the SOS-adjusted last-5 FIP with the probable starter's
    season FIP (the stable anchor) when a real season sample exists."""
    sp = _adjusted_fip(team.starter_fip_last5, team.starter_ip_last5,
                       team.sos.get("sp_opp_woba"), team.sos.get("sp_opp_win"))
    if team.starter_fip_season is not None:
        sp = (SEASON_SP_WEIGHT * team.starter_fip_season + (1 - SEASON_SP_WEIGHT) * sp
              if sp is not None else team.starter_fip_season)
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
    return win_condition_core(team.games_last5, combined_fip(team),
                              _rpg(opp.games_last5), combined_fip(opp))


def win_condition_core(team_games_last5: list, team_fip: float | None,
                       opp_rpg: float, opp_fip: float | None) -> dict:
    """The bars + SOS-adjusted last-5 back-test from raw inputs. Shared by the live
    path (win_condition, fed starter+bullpen FIP) and the calibration tool (fed a
    season-FIP stand-in). FIPs fall back to the league average when unknown."""
    team_rpg = _rpg(team_games_last5)
    team_fip = team_fip or LEAGUE_FIP
    opp_fip = opp_fip or LEAGUE_FIP

    exp_opp_runs = opp_rpg * (team_fip / LEAGUE_FIP)
    exp_own_runs = team_rpg * (opp_fip / LEAGUE_FIP)
    runs_to_win = math.floor(exp_opp_runs) + 1
    runs_to_allow = max(1, math.floor(exp_own_runs))

    scored = prevent = complete = won = outhit = 0
    per_game = []
    for g in team_games_last5:
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
    n = len(team_games_last5)
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
        "avg_opp_win_pct_faced": round(sum(g.get("opp_win", 0.5) for g in team_games_last5) / n, 3),
        "per_game": per_game,
    }


# --- decision -----------------------------------------------------------------
def _blended_iso(team: Team) -> float | None:
    line = _blend_offense_lines(offense_line(team.offense),
                                offense_line(team.season_offense))
    return line.get("iso_neutral") if line else None


def _blended_kpct(team: Team) -> float | None:
    line = _blend_offense_lines(offense_line(team.offense),
                                offense_line(team.season_offense))
    return line.get("k_pct") if line else None


def statistical_favorite(game: Game, cons: tuple[int, int] | None = None) -> tuple[Team, float, float]:
    hs, as_ = team_score(game.home) + HOME_FIELD, team_score(game.away)   # home-field bump
    # consistency tilt: (home hits, away hits) out of 5 from the SOS-adjusted
    # back-test - the steadier side gets CONS_MARGIN_W per game of difference
    if cons is not None:
        cdiff = cons[0] - cons[1]
        if cdiff > 0:
            hs += CONS_MARGIN_W * cdiff
        elif cdiff < 0:
            as_ += CONS_MARGIN_W * -cdiff
    # BvP nudge, innings-projected: each lineup faces the opposing STARTER for his
    # projected innings and the (available-arms) PEN for the rest, so each side's
    # expected matchup OPS = starter_share * starter BvP + (1 - share) * pen BvP.
    b, pen = bvp_read(game), pen_bvp_read(game)
    pen_ok = pen is not None and pen["total_pa"] >= PEN_BVP_MIN_PA

    def _starter_share(opposing: Team) -> float:
        ip = getattr(opposing, "starter_proj_ip", None)
        if not ip:
            return 1 - BVP_PEN_SHARE
        return max(PROJ_IP_CLAMP[0], min(PROJ_IP_CLAMP[1], ip)) / 9.0

    def _expected(side: str, opposing: Team) -> float | None:
        sv = b[f"{side}_eff"] if b else None
        pv = pen[f"{side}_ops"] if pen_ok else None
        if sv is not None and pv is not None:
            share = _starter_share(opposing)
            return share * sv + (1 - share) * pv
        return sv if sv is not None else pv

    eh, ea = _expected("home", game.away), _expected("away", game.home)
    gap = (eh - ea) if eh is not None and ea is not None else None
    if gap is not None and abs(gap) >= BVP_FLOOR:
        tilt = min(abs(gap) - BVP_FLOOR, BVP_TILT_CAP)
        if gap > 0:
            hs += tilt
        else:
            as_ += tilt
    # weather x power (every non-dome game): warm/windy air carries and helps the
    # higher-ISO lineup; cold suppresses power and helps the contact side. The
    # tilt is continuous in temp/wind and the ISO gap, so a neutral 70F/calm game
    # nets ~0 while the extremes push toward the cap.
    wx = getattr(game, "weather", None)
    if wx and wx.get("roof") != "dome":
        hi, ai = _blended_iso(game.home), _blended_iso(game.away)
        if hi is not None and ai is not None and abs(hi - ai) >= WX_ISO_FLOOR:
            temp = wx.get("temp_f")
            wind = wx.get("wind_mph") or 0
            carry = max(0.0, wind - WX_WIND_CALM) * WX_WIND_PER_MPH
            if temp is not None:
                carry += (temp - WX_NEUTRAL_TEMP) / 10.0 * WX_TEMP_PER10
            raw = carry * (hi - ai) * WX_GAP_SCALE
            tilt = max(-WX_TILT_CAP, min(WX_TILT_CAP, raw))
            if tilt >= 0:
                hs += tilt
            else:
                as_ += -tilt
    # umpire x strikeouts: a big-zone HP ump hurts the strikeout-prone lineup
    # more - tilt toward the lower-K side (only known near first pitch, so this
    # lands at the pre-game refresh; fail-soft when unknown)
    u = getattr(game, "ump_tend", None)
    if (u and u.get("games", 0) >= UMP_MIN_GAMES
            and (u.get("k_extra") or 0) >= UMP_K_EXTRA):
        hk, ak = _blended_kpct(game.home), _blended_kpct(game.away)
        if hk is not None and ak is not None and abs(hk - ak) >= UMP_KGAP_FLOOR:
            tilt = min(UMP_TILT_SCALE * abs(hk - ak), UMP_TILT_CAP)
            if hk < ak:      # home lineup strikes out less -> zone helps them
                hs += tilt
            else:
                as_ += tilt
    winner = game.home if hs >= as_ else game.away
    return winner, hs, as_


def _match_consensus(game: Game, consensus: dict) -> dict | None:
    """The consensus row whose two abbreviations are this game's two teams."""
    for sides in consensus.values():
        if _matches(game, [sides["away"]["abbr"], sides["home"]["abbr"]]):
            return sides
    return None


# covers odds-page abbreviations vs MLB abbreviations differ for a few teams;
# canonicalize so the slate-line lookup matches.
_ABBR_ALIAS = {"WAS": "WSH", "CHW": "CWS", "SDP": "SD", "SFG": "SF", "TBR": "TB",
               "KCR": "KC", "AZ": "ARI", "WSN": "WSH"}


def _canon_abbr(ab: str) -> str:
    ab = (ab or "").upper()
    return _ABBR_ALIAS.get(ab, ab)


def find_slate_line(game: Game, slate: list) -> dict | None:
    """The odds-page line entry for this game, matched by team abbreviation."""
    a, h = _canon_abbr(game.away.abbreviation), _canon_abbr(game.home.abbreviation)
    for e in slate:
        if _canon_abbr(e["away_abbr"]) == a and _canon_abbr(e["home_abbr"]) == h:
            return e
    return None


def _implied(ml) -> float:
    """American moneyline -> implied win probability."""
    ml = int(ml)
    return 100.0 / (ml + 100) if ml > 0 else (-ml) / (float(-ml) + 100)


def line_confirms(side: str, lm: dict | None) -> tuple[bool | None, dict]:
    """Did the line move TOWARD a pick on `side` ('away'/'home')? Reverse line
    movement (the pick's price shortening) = sharp money confirming the fade.
    Returns (confirms, detail). confirms is None when the line is unavailable."""
    if not lm or lm.get(f"{side}_open") is None or lm.get(f"{side}_current") is None:
        return None, {"status": "unknown", "reason": "no line data"}
    o, c = lm[f"{side}_open"], lm[f"{side}_current"]
    shift = round(_implied(c) - _implied(o), 3)
    arrow = f"{o:+d}→{c:+d}"
    info = {"open": o, "current": c, "implied_shift": shift}
    if shift == 0:
        info.update(status="flat", reason=f"line hasn't moved ({arrow})")
    elif shift < 0:
        info.update(status="contradicts", reason=f"line moved away from the pick ({arrow}, {shift:+.1%})")
    elif shift < LINE_CONFIRM_MIN:
        info.update(status="soft",
                    reason=f"only a slight move our way, below the {LINE_CONFIRM_MIN:.0%} signal floor ({arrow}, {shift:+.1%})")
    elif shift >= LINE_BIG:
        info.update(status="caution",
                    reason=f"big move our way ({arrow}, {shift:+.1%}) — usually a pitcher change/news, verify before trusting")
    else:
        tier = "strong" if shift >= LINE_STRONG else "moderate"
        info.update(status="confirms", tier=tier,
                    reason=f"{tier} sharp move toward the pick ({arrow}, {shift:+.1%})")
    return info["status"] == "confirms", info


def _consensus_home_lean(game: Game, sides: dict) -> float | None:
    """covers consensus as a lean toward the home team, in [-1, 1]."""
    home_pct = away_pct = None
    for s in (sides["away"], sides["home"]):
        t = _resolve(game, s["abbr"])
        if t.team_id == game.home.team_id:
            home_pct = s["pct"]
        elif t.team_id == game.away.team_id:
            away_pct = s["pct"]
    if home_pct is None or away_pct is None:
        return None
    return (home_pct - away_pct) / 100.0


def public_majority(game, consensus, forum_counts, reddit_counts=None,
                    wiki_counts=None, extra_public=None) -> tuple[Team | None, dict]:
    """The side the betting public is on. The forum mention tally is weighted
    higher than covers consensus (PUBLIC_W_FORUM > PUBLIC_W_CONSENSUS); both are
    turned into a home-team lean and blended, and the blend's sign picks the side.
    Either signal alone decides if it's the only one present. detail carries both
    raw signals, their leans, the blend, and whether they agree.

    The Reddit forum tally is recorded (detail['reddit'/'reddit_lean']) for the
    cross-check and the board, but is deliberately NOT blended into the side
    decision yet - it's a new signal we watch before letting it move picks."""
    detail = {"consensus": None, "forum": None, "agree": None,
              "forum_lean": None, "consensus_lean": None, "blended_lean": None,
              "reddit": None, "reddit_lean": None, "wiki": None, "wiki_lean": None,
              "books": {}}

    # Every '*_bets' source (S&O / VSiN / OddsShark ticket shares) is the same kind
    # of signal as covers consensus, so each votes on the public side. '*_money'
    # (dollar shares) never joins the fade blend - it's the sharp side, handled in
    # public_crosscheck as the money flag.
    book_leans: list[float] = []
    for name in sorted((extra_public or {})):
        if not name.endswith("_bets"):
            continue
        for row in extra_public[name]:
            side, pcts = _source_side(game, row)
            if side and pcts:
                ap, hp = pcts
                lean = (hp - ap) / 100.0
                detail["books"][name] = {"away": ap, "home": hp, "lean": round(lean, 3)}
                if lean:
                    book_leans.append(lean)
                break

    rh, ra = (reddit_counts or {}).get(game.home.name, 0), (reddit_counts or {}).get(game.away.name, 0)
    if rh or ra:
        detail["reddit"] = {"home": rh, "away": ra}
        detail["reddit_lean"] = round((rh - ra) / (rh + ra), 3)

    # Wikipedia attention: recorded for the board + comparison, but display-only -
    # it does NOT vote in the cross-check or the public-side blend until the
    # calibration (wiki_calibrate.py) shows fading the higher-attention team has edge.
    wh, wa = (wiki_counts or {}).get(game.home.name, 0), (wiki_counts or {}).get(game.away.name, 0)
    if wh or wa:
        detail["wiki"] = {"home": wh, "away": wa}
        detail["wiki_lean"] = round((wh - wa) / (wh + wa), 3)

    # consensus -> home lean
    cons_lean = None
    sides = _match_consensus(game, consensus)
    if sides:
        away, home = sides["away"], sides["home"]
        cons_lean = _consensus_home_lean(game, sides)
        top = away if away["pct"] >= home["pct"] else home
        detail["consensus"] = {"pick": top["abbr"],
                               "pcts": {away["abbr"]: away["pct"], home["abbr"]: home["pct"]}}

    # forum -> home lean (the heavier signal)
    forum_lean = None
    hc, ac = forum_counts.get(game.home.name, 0), forum_counts.get(game.away.name, 0)
    if hc or ac:
        forum_lean = (hc - ac) / (hc + ac)
        detail["forum"] = {"pick": (game.home if hc >= ac else game.away).name,
                           "home": hc, "away": ac}

    # weighted blend toward the home team (forum weighted higher); a tied signal
    # (lean 0) contributes nothing, so the other one breaks the tie
    parts = []
    if forum_lean:
        parts.append((PUBLIC_W_FORUM, forum_lean))
    if cons_lean:
        parts.append((PUBLIC_W_CONSENSUS, cons_lean))
    for lean in book_leans:
        parts.append((PUBLIC_W_SOBETS, lean))
    majority = None
    if parts:
        blended = sum(w * l for w, l in parts) / sum(w for w, _ in parts)
        detail["blended_lean"] = round(blended, 3)
        majority = game.home if blended > 0 else game.away if blended < 0 else None

    detail["forum_lean"] = None if forum_lean is None else round(forum_lean, 3)
    detail["consensus_lean"] = None if cons_lean is None else round(cons_lean, 3)
    if forum_lean and cons_lean:
        detail["agree"] = (forum_lean > 0) == (cons_lean > 0)

    return majority, detail


def _source_side(game: Game, row: dict) -> tuple[str | None, tuple[int, int] | None]:
    """Which side ('home'/'away') a public-% row says the public is on, matched to
    this game by abbreviation (orientation-agnostic). (None, None) if it isn't this
    game or the percentages are missing."""
    a, h = _canon_abbr(game.away.abbreviation), _canon_abbr(game.home.abbreviation)
    ra, rh = _canon_abbr(row.get("away_abbr", "")), _canon_abbr(row.get("home_abbr", ""))
    if {ra, rh} != {a, h}:
        return None, None
    ap, hp = row.get("away_pct"), row.get("home_pct")
    if ap is None or hp is None:
        return None, None
    if ra == h:                      # row lists the teams home-first; reorient
        ap, hp = hp, ap
    return ("away" if ap >= hp else "home"), (round(ap), round(hp))


def public_crosscheck(game: Game, majority: Team | None, detail: dict,
                      extra_public: dict | None) -> dict:
    """Corroborate the public read across every available source (covers consensus,
    the covers forum tally, and each extra public-% site) and sanity-check it.

    A single book's public % can be misleading, so we only TRUST the read enough to
    fade it when at least two independent sources agree on the side. With fewer than
    two opinions we can't cross-check, so we don't penalize it (keeps the system live
    while new-source selectors are still being tuned) — but we mark it unconfirmed.

    Returns {sources, majority_side, agree, dissent, trusted, verdict, note, flags}.
    `line` is filled in later (main._attach_line) from the slate.
    """
    out = {"sources": [], "majority_side": None, "agree": 0, "dissent": 0,
           "trusted": True, "verdict": "no public read", "note": "no public lean to check",
           "flags": [], "line": "unknown", "money": "unknown", "money_side": None}
    # money side is computed even without a public majority - the stay-away pile
    # fades the money on games with no other read
    money_sides0: list[str] = []
    for name, rows in (extra_public or {}).items():
        if not name.endswith("_money"):
            continue
        for row in rows:
            side, _ = _source_side(game, row)
            if side:
                money_sides0.append(side)
            break
    out["money_side"] = (money_sides0[0]
                         if money_sides0 and len(set(money_sides0)) == 1 else None)
    if majority is None:
        return out
    out["majority_side"] = "home" if majority.team_id == game.home.team_id else "away"

    opinions: list[tuple[str, str, tuple | None]] = []
    if detail.get("consensus_lean"):
        opinions.append(("covers", "home" if detail["consensus_lean"] > 0 else "away",
                         tuple((detail.get("consensus") or {}).get("pcts", {}).values()) or None))
    if detail.get("forum_lean"):
        opinions.append(("forum", "home" if detail["forum_lean"] > 0 else "away", None))
    if detail.get("reddit_lean"):
        opinions.append(("reddit", "home" if detail["reddit_lean"] > 0 else "away", None))
    # `*_money` sources (share of dollars) aren't public-consensus votes - they're the
    # sharp signal, handled separately below. Only ticket/consensus sources corroborate.
    money_sides: list[str] = []
    for name, rows in (extra_public or {}).items():
        for row in rows:
            side, pcts = _source_side(game, row)
            if not side:
                continue
            if name.endswith("_money"):
                money_sides.append(side)
            else:
                opinions.append((name, side, pcts))
            break
    # unanimous money sources -> that side; disagreement -> no clean money read
    money_side = money_sides[0] if money_sides and len(set(money_sides)) == 1 else None
    money_split = len(set(money_sides)) > 1

    ms = out["majority_side"]
    out["sources"] = [{"name": n, "side": s, "agrees": s == ms} for n, s, _ in opinions]
    out["agree"] = sum(1 for _, s, _ in opinions if s == ms)
    out["dissent"] = sum(1 for _, s, _ in opinions if s != ms)

    # sanity: a source whose two percentages don't roughly complement (sum ~100) is
    # suspect markup or a bad read - surface it rather than silently trusting it.
    for n, _, pcts in opinions:
        if pcts and len(pcts) >= 2:
            tot = sum(pcts[:2])
            if not 80 <= tot <= 120:
                out["flags"].append(f"{n} % looks off (sums {int(tot)}%)")

    n = len(opinions)
    out["trusted"] = (n < 2) or (out["agree"] > out["dissent"])
    dis_names = [s["name"] for s in out["sources"] if not s["agrees"]]
    if n < 2:
        out["verdict"], out["note"] = "unconfirmed", "only one public source — can't cross-check"
    elif out["dissent"] == 0:
        out["verdict"], out["note"] = "corroborated", f"all {n} sources agree on the public side"
    elif out["trusted"]:
        out["verdict"] = "mostly agrees"
        out["note"] = f"{out['agree']}/{n} sources agree ({', '.join(dis_names)} differ)"
    else:
        out["verdict"] = "sources split"
        out["note"] = f"sources disagree on the public side ({', '.join(dis_names)} differ)"

    # Sharp signal: where the MONEY is vs where the tickets (public) are. Money on
    # the opposite side from the public is the classic "the % doesn't match the
    # dollars" tell - and a tailwind when it's on our fade side.
    out["money_side"] = money_side
    if money_side:
        out["money"] = "with public" if money_side == ms else "against public"
        if out["money"] == "against public":
            out["flags"].append("money is on the other side from the public tickets")
    elif money_split:
        out["money"] = "sources split"
        out["flags"].append("money sources disagree")
    return out


def betting_lines(game: Game, consensus: dict, majority_team: Team | None = None) -> dict | None:
    """Each side's moneyline, split into the public-majority side and the side the
    public is fading. The majority side follows the overall public read
    (`majority_team`, forum-weighted) when given, else falls back to the higher
    consensus %. Returns None if this game has no consensus row. (covers' MLB
    consensus is moneyline-only - no run line.)"""
    sides = _match_consensus(game, consensus)
    if not sides:
        return None
    away, home = sides["away"], sides["home"]
    majority, non_majority = (away, home) if away["pct"] >= home["pct"] else (home, away)
    if majority_team is not None:
        for s in (away, home):
            if _resolve(game, s["abbr"]).team_id == majority_team.team_id:
                majority, non_majority = s, (home if s is away else away)
                break

    def fmt(side: dict) -> dict:
        return {
            "team": _resolve(game, side["abbr"]).name,
            "consensus_pct": side["pct"],
            "moneyline": side["moneyline"],
        }

    return {"majority": fmt(majority), "non_majority": fmt(non_majority)}


BVP_SHRINK_PA = 50   # exact-BvP PA at which the exact number gets 50% weight


def _bvp_effective(exact_ops, exact_pa, hand_ops, hand_pa):
    """Shrink a tiny exact-BvP OPS toward the big-sample vs-hand OPS. With exact_pa
    PA the exact number gets exact_pa/(exact_pa+BVP_SHRINK_PA) of the weight; the
    rest goes to the vs-hand backbone. Falls back to whichever side exists."""
    if exact_ops is not None and exact_pa and hand_ops is not None:
        w = exact_pa / (exact_pa + BVP_SHRINK_PA)
        return round(w * exact_ops + (1 - w) * hand_ops, 3), exact_pa + hand_pa
    if hand_ops is not None:
        return round(hand_ops, 3), hand_pa
    if exact_ops is not None:
        return round(exact_ops, 3), exact_pa
    return None, 0


def bvp_read(game: Game) -> dict | None:
    """Batter-vs-pitcher edge: which lineup projects to hit the OPPOSING starter
    better. The tiny exact career-BvP OPS is shrunk toward the team's big-sample OPS
    vs that starter's HAND, so the read is robust even when the exact sample is a
    handful of PA. Display context only. None when neither read exists for a side."""
    h, a = game.home, game.away
    h_eff, h_pa = _bvp_effective(h.bvp_ops, h.bvp_pa, h.bvp_hand_ops, h.bvp_hand_pa)
    a_eff, a_pa = _bvp_effective(a.bvp_ops, a.bvp_pa, a.bvp_hand_ops, a.bvp_hand_pa)
    if h_eff is None or a_eff is None:
        return None
    gap = round(h_eff - a_eff, 3)
    return {
        "home_eff": h_eff, "away_eff": a_eff,
        "home_ops": h.bvp_ops, "away_ops": a.bvp_ops,      # exact (small sample)
        "home_pa": h.bvp_pa, "away_pa": a.bvp_pa,
        "home_hand_ops": h.bvp_hand_ops, "away_hand_ops": a.bvp_hand_ops,  # vs-hand (big)
        "home_hand_pa": h.bvp_hand_pa, "away_hand_pa": a.bvp_hand_pa,
        "total_pa": h_pa + a_pa,
        "edge_team": (h.name if gap > 0 else a.name) if gap else None,
        "gap": abs(gap),
        "meaningful": abs(gap) >= BVP_FLOOR,
    }


def pen_bvp_read(game: Game) -> dict | None:
    """Bullpen BvP: each lineup's career OPS vs the OPPOSING bullpen - the arms
    likely to close the game out. Exact career numbers only (the pen mixes hands,
    so no vs-hand backbone); meaningful needs a real gap AND a real sample.
    Display context only."""
    h, a = game.home, game.away
    if h.pen_bvp_ops is None or a.pen_bvp_ops is None:
        return None
    gap = round(h.pen_bvp_ops - a.pen_bvp_ops, 3)
    total = h.pen_bvp_pa + a.pen_bvp_pa
    return {
        "home_ops": h.pen_bvp_ops, "away_ops": a.pen_bvp_ops,
        "home_pa": h.pen_bvp_pa, "away_pa": a.pen_bvp_pa, "total_pa": total,
        "edge_team": (h.name if gap > 0 else a.name) if gap else None,
        "gap": abs(gap),
        "meaningful": abs(gap) >= BVP_FLOOR and total >= 100,
    }


def evaluate_game(game: Game, consensus: dict, forum_counts: dict,
                  extra_public: dict | None = None, reddit_counts: dict | None = None,
                  wiki_counts: dict | None = None) -> dict:
    # platoon depends on the matchup, so set it before scoring
    home_opp = game.away.probable_pitcher.hand if game.away.probable_pitcher else ""
    away_opp = game.home.probable_pitcher.hand if game.home.probable_pitcher else ""
    game.home.platoon_factor = platoon_factor(game.home.offense.get("bats", []), home_opp)
    game.away.platoon_factor = platoon_factor(game.away.offense.get("bats", []), away_opp)

    # consistency first: both sides' last-5 win-condition hits feed the margin tilt
    wc_home = win_condition(game.home, game.away)
    wc_away = win_condition(game.away, game.home)
    cons_pair = None
    if wc_home and wc_away:
        cons_pair = (wc_home["back_test"]["complete_win_condition"],
                     wc_away["back_test"]["complete_win_condition"])

    adv_team, hs, as_ = statistical_favorite(game, cons_pair)
    majority, majority_detail = public_majority(game, consensus, forum_counts,
                                                reddit_counts, wiki_counts, extra_public)

    # Cross-check the public read across all sources (covers % + forum + extras);
    # we only fade a read that's corroborated (see public_crosscheck).
    crosscheck = public_crosscheck(game, majority, majority_detail, extra_public)
    public_trusted = crosscheck["trusted"]

    # Precondition: there's a public read AND the statistical favorite is the side
    # the public is fading (keeps the public-vs-stats thesis).
    public_edge = bool(majority) and adv_team.team_id != majority.team_id

    # consistency (the former win condition) - a signal AND a margin tilt now.
    adv_wc = wc_home if adv_team.team_id == game.home.team_id else wc_away
    cons_hits = adv_wc["back_test"]["complete_win_condition"] if adv_wc else 0
    edge_margin = abs(hs - as_)
    edge_conf = _clamp01(edge_margin / EDGE_FULL)
    # Fade strength now requires an ACTUAL fade (public on the other side) and is
    # scaled by how many sources corroborate the public read - a lean backed by a
    # fade that 3 sources agree on outranks one where the public read is shaky.
    raw_fade = _clamp01(abs(majority_detail.get("blended_lean") or 0.0))
    corrob = (crosscheck["agree"] / len(crosscheck["sources"])
              if crosscheck["sources"] else 1.0)
    fade_conf = raw_fade * corrob if public_edge else 0.0
    confidence = round(W_EDGE * edge_conf + W_FADE * fade_conf, 3)  # display strength

    # Hard gate: public fade AND a real stat edge. The third must-have (line moved
    # in our favor) is applied in main._attach_line, which downgrades a flagged
    # pick whose line doesn't confirm.
    edge_strong = edge_margin >= EDGE_THRESHOLD
    flagged = public_edge and edge_strong and public_trusted

    if flagged:
        status, reason = "pick", "public fade + stat edge cleared (pending line confirm)"
    elif not public_edge:
        if not majority:
            status, reason = "lean", "no public lean on this game"
        else:
            status, reason = "lean", f"public is also on {adv_team.name} (no fade)"
    elif not edge_strong:
        status, reason = "lean", (f"stat edge too small (margin {round(edge_margin, 2)} "
                                  f"< {EDGE_THRESHOLD} threshold)")
    else:
        status, reason = "lean", f"public read not corroborated — {crosscheck['note']}"

    return {
        "game_pk": game.game_pk,
        "matchup": f"{game.away.name} @ {game.home.name}",
        "away_abbr": game.away.abbreviation or game.away.name,
        "home_abbr": game.home.abbreviation or game.home.name,
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
        "public_check": crosscheck,
        "bvp": bvp_read(game),
        "bvp_pen": pen_bvp_read(game),
        "betting_lines": betting_lines(game, consensus, majority),
        "consistency": {
            "home": wc_home,
            "away": wc_away,
        },
        "pick_criteria": {
            "status": status,
            "reason": reason,
            "advantage_team": adv_team.name,
            "public_edge": public_edge,
            "public_trusted": public_trusted,
            "edge_strong": edge_strong,
            "confidence": confidence,
            "edge_threshold": EDGE_THRESHOLD,
            "components": {
                "stat_edge": {"margin": round(edge_margin, 3), "strength": round(edge_conf, 3),
                              "weight": W_EDGE},
                "public_fade": {"blended_lean": majority_detail.get("blended_lean"),
                                "strength": round(fade_conf, 3), "weight": W_FADE},
                "consistency": {"hits": cons_hits, "context_only": True},
            },
            "consistency_hits": cons_hits,
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
    return _name_hit(game.home, names) and _name_hit(game.away, names)


def _name_hit(team: Team, names: list[str]) -> bool:
    """True if any covers label identifies this team. covers uses abbreviations
    (e.g. 'Bos'), so match team.abbreviation as an exact token first, then fall
    back to the nickname as a substring."""
    names_l = [n.lower() for n in names]
    abbr = (team.abbreviation or "").lower()
    if abbr and abbr in names_l:
        return True
    nick = team.name.lower().split()[-1] if team.name else ""
    return bool(nick) and nick in " ".join(names_l)


def _resolve(game: Game, label: str) -> Team:
    low = label.lower()
    if (game.home.abbreviation or "").lower() == low:
        return game.home
    if (game.away.abbreviation or "").lower() == low:
        return game.away
    home_nick = game.home.name.lower().split()[-1] if game.home.name else ""
    return game.home if home_nick and home_nick in low else game.away
