"""
Our own numbers for first-five runs, strikeouts and hits — on every game.

WHY THESE EXIST
Asked for something on the board even on nights with no pick. They are also the
missing half of the market log: `market_log` records what the book charges for
the F5 total and the starter's strikeout line, and this records what WE think,
so the two accumulate side by side. That pairing is what the pre-registered
test in `totals_signal` will need, and neither half is any use alone.

NOT BETS. Nothing is staked, nothing enters a ledger, no pick changes. The
honest status is untested: the only input measured against real scores is
pitching, at r=+0.180 against full-game runs and +0.138 against the first five
(`totals_signal.py`), and the market prices starting pitching before anything
else. So treat a disagreement as a thing to log, not a thing to bet.

NOTHING IS FITTED
Same discipline as the rest of the repo. The mappings are plain proportional
scalings off league means we measured ourselves - 8.66 full-game runs, 4.71
through five, a 54% share that the market's own F5/full line ratio matches
exactly - not coefficients tuned to make a backtest look good. A crude scaling
that is honest beats a fitted one that is not, and when the logged lines
accumulate the test will say which inputs deserve weight.
"""

from __future__ import annotations

import logging

from . import mlb_api

log = logging.getLogger("projections")

# The league means these scalings hang off, re-measured in totals_model.py over
# 1286 finished board games - up from the 251 totals_signal.py had. Not a tuned
# coefficient: the constant is DEFINED as the league mean of the thing being
# projected, and this is a better estimate of the same quantity. It also removes
# most of a measured bias, the projection having run 0.45 runs cold full-game
# and 0.35 cold through five on the old pair.
LEAGUE_FULL_RUNS = 8.92    # was 8.66 on 251 games
LEAGUE_F5_RUNS = 4.96      # was 4.71; 55.6% of the game, not the 54% assumed
LEAGUE_FIP = 4.20          # the league baseline analysis.py works from
LEAGUE_K9 = 8.6
STARTER_IP_DEFAULT = 5.3
CLAMP = (0.70, 1.40)

# THE UMPIRE IS DELIBERATELY ABSENT, and it was asked for. Measured in
# totals_model.py over 1038 board games, every one of them out of sample for
# the `ump_tendencies_2026.json` table (built through 2026-07-02):
#
#   k_extra vs the game's actual strikeouts   r = -0.044
#   high-k_extra third of umpires             16.36 K/gm
#   low-k_extra third                         17.14 K/gm   -> gap -0.78
#   k_extra vs what the K projection MISSES   r = +0.012
#   applying it as a multiplier, dMAE         [-0.008, +0.018]
#
# The sign is BACKWARDS - umpires the table calls big-zone presided over fewer
# strikeouts, not more - and the magnitude is inside noise at this sample. An
# umpire term would be decoration. See `totals_model.md` for whether the
# tendency is a stable trait at all; if a rebuilt table ever shows one, the
# multiplier is `totals_model.ump_k_mult` and this is where it goes.


def _clamp(v, lo=CLAMP[0], hi=CLAMP[1]):
    return max(lo, min(hi, v))


def _fip(side: dict) -> float | None:
    """Starter FIP, last-5 first - it measured strongest against runs."""
    for k in ("starter_fip_last5", "starter_fip_season"):
        v = (side or {}).get(k)
        if isinstance(v, (int, float)) and v > 0:
            return float(v)
    return None


def _pen_fip(side: dict) -> float | None:
    v = (side or {}).get("bullpen_fip_last5")
    return float(v) if isinstance(v, (int, float)) and v > 0 else None


def runs(sa: dict) -> dict:
    """Projected full-game and first-five runs for the game.

    THE TWO NUMBERS DO NOT SHARE A MULTIPLIER, because they are not pitched by
    the same people. The starters pitch the first five, so that one is scaled by
    starter FIP alone. The full game is scaled by starter and bullpen FIP
    weighted by INNINGS - `STARTER_IP_DEFAULT` of nine from the starters, the
    rest from the pen.

    That is mechanism, and the measurements agree twice over. Bullpen FIP
    correlates +0.139 with full-game runs and +0.030 with the first five
    (`totals_signal.md`), exactly the asymmetry the innings split implies. And
    the split beats the old shared multiplier head to head on 1284 games: MAE
    3.60 -> 3.53 full-game, r +0.075 -> +0.097, day-block bootstrap dMAE
    [-0.105, -0.038], an interval entirely below zero (`totals_model.md`). The
    first-five number is unchanged by construction, which is why its row in
    that table is identical.

    Park and weather are deliberately ABSENT: they are game-level and affect
    both sides, which is right for a total - but they measured at r=+0.023 and
    +0.101 against actual runs, so adding them would dress the number up
    without improving it.
    """
    fips = [f for f in (_fip(sa.get("home")), _fip(sa.get("away")))
            if f is not None]
    if not fips:
        return {}
    sp = sum(fips) / len(fips)
    m_f5 = _clamp(sp / LEAGUE_FIP)
    pens = [f for f in (_pen_fip(sa.get("home")), _pen_fip(sa.get("away")))
            if f is not None]
    if pens:
        pen = sum(pens) / len(pens)
        w = STARTER_IP_DEFAULT / 9.0
        m_full = _clamp((w * sp + (1 - w) * pen) / LEAGUE_FIP)
        basis = (f"starter FIP {sp:.2f} + pen {pen:.2f} weighted "
                 f"{w:.0%}/{1 - w:.0%} by innings vs league {LEAGUE_FIP:.2f} "
                 f"(full x{m_full:.2f}, F5 x{m_f5:.2f} starters only)")
    else:
        # no pen number on this board: fall back to the starters for both, which
        # is what shipped before the split
        m_full = m_f5
        basis = (f"starter FIP {sp:.2f} vs league {LEAGUE_FIP:.2f} "
                 f"(x{m_full:.2f}, no bullpen number)")
    return {"full": round(LEAGUE_FULL_RUNS * m_full, 2),
            "f5": round(LEAGUE_F5_RUNS * m_f5, 2),
            "basis": basis}


def strikeouts(pitcher_id: int, name: str, season: int,
               opp_k_pct: float | None) -> dict | None:
    """Projected strikeouts for one starter.

    His own K/9 over his expected innings, nudged by how often the lineup he
    faces strikes out. Both numbers are his and theirs - nothing is fitted.
    """
    if not pitcher_id:
        return None
    try:
        line = mlb_api.pitcher_season_line(pitcher_id, season)
    except Exception as exc:
        log.warning("K projection unavailable for %s: %s", name, exc)
        return None
    ip, gs = line.get("ip") or 0, line.get("gs") or 0
    ip_gs, k_gs = line.get("ip_gs") or 0, line.get("k_gs") or 0
    if ip < 20:
        return None
    # STARTS ONLY for both rates. Dividing all-appearance innings by games
    # STARTED overstates how long he goes for anyone who also relieved, and
    # that one line was worth +0.71 strikeouts of bias on every projection
    # (measured over 2353 starts in totals_model.md). A pitcher with no
    # recorded starts yet falls back to the all-appearance rate.
    if ip_gs > 0 and gs >= 3:
        k9 = k_gs * 9.0 / ip_gs
        exp_ip = ip_gs / gs
    else:
        k9 = (line.get("k") or 0) * 9.0 / ip
        exp_ip = STARTER_IP_DEFAULT
    opp = 1.0
    note = ""
    if isinstance(opp_k_pct, (int, float)) and opp_k_pct > 0:
        opp = _clamp(opp_k_pct / 0.225, 0.85, 1.15)   # ~22.5% league K rate
        note = f" · lineup K {opp_k_pct:.1%} (x{opp:.2f})"
    return {"pitcher": name,
            "proj": round(k9 * exp_ip / 9.0 * opp, 2),
            "k9": round(k9, 2), "exp_ip": round(exp_ip, 1),
            "basis": f"{k9:.2f} K/9 over {exp_ip:.1f} IP{note}"}


def hits(side: dict) -> dict | None:
    """Projected team hits: batting average over expected at-bats.

    ~38 plate appearances a game for a side, and roughly 88% of them are at
    bats once walks and sacrifices come out.
    """
    off = (side or {}).get("offense") or {}
    avg = off.get("avg")
    if not isinstance(avg, (int, float)) or avg <= 0:
        return None
    ab = 38.0 * 0.88
    return {"proj": round(float(avg) * ab, 2),
            "basis": f"{avg:.3f} AVG over ~{ab:.0f} AB"}


def attach(result: dict, game, season: int) -> None:
    """Write projections onto a board row. Fails soft - a projection must
    never cost the board a pick."""
    try:
        sa = result.get("statistical_advantage") or {}
        out = {}
        r = runs(sa)
        if r:
            out["runs"] = r
        ks = []
        for side, team in (("home", game.home), ("away", game.away)):
            sp = getattr(team, "probable_pitcher", None)
            opp_side = "away" if side == "home" else "home"
            opp_k = ((sa.get(opp_side) or {}).get("offense") or {}).get("k_pct")
            if sp and getattr(sp, "player_id", None):
                k = strikeouts(sp.player_id, sp.name, season, opp_k)
                if k:
                    ks.append(k)
        if ks:
            out["strikeouts"] = ks
        h = {}
        for side, team in (("home", game.home), ("away", game.away)):
            v = hits(sa.get(side))
            if v:
                h[team.name] = v
        if h:
            out["hits"] = h
        if out:
            out["status"] = ("projection only — not a bet, untested; "
                             "logged beside the market line for a later test")
            result.setdefault("pick_criteria", {})["projections"] = out
    except Exception as exc:
        log.warning("projections failed for %s: %s",
                    result.get("matchup"), exc)
