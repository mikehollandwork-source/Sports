"""
The consensus rule - the board's pick logic as of 2026-07-28.

WHY THIS REPLACED THE FADE SYSTEM
The old board bet the statistically-better side whenever the PUBLIC was on the
other team (fade the public). Over 168 live bets that went 90-78 / -11.09u
(-6.6%), and a full holdout audit showed every variant of it negative
out-of-sample. The market-signal backtest found the reason: the premise was
inverted. Backing the side the money is on beat backing the side it is against,
in both windows:

  handle AGAINST tickets (the old premise) ... 12-18 (40%) · -23.5%
  handle WITH tickets + order book confirms .. 46-22 (68%) · +12.5% all-time,
                                               19-9  (68%) · +10.2% holdout

THE RULE
Back the CONSENSUS side - the ticket majority, when the handle agrees with it -
but only when Polymarket's pre-game order book confirms that same side. The
order-book filter is what carries the edge (consensus alone is ~breakeven out of
sample); the book's own vig positioning added nothing measurable, so it is not
required.

Confirmation = on the consensus side, the pre-game mid price DRIFTED UP over the
run-up, or resting BID size outweighs ask size. The book log stores the
advantage side's token, so when the consensus is the other team the reading is
inverted.

CAVEATS, stated plainly: n=68 all-time / 28 holdout. It is the only strategy
tested this session that was positive in BOTH windows and it has a mechanism
(money convergence is information), but it is not yet proven at scale. It needs
PM readings to exist for the day, so the first board of a slate - built before
the order-book cron has logged anything - will have no picks.
"""

from __future__ import annotations

import datetime as dt
import logging

from . import pm_books

log = logging.getLogger("consensus")

MAX_SPREAD = 0.15      # wider than this is not a real two-sided market
MIN_READINGS = 2       # need a run-up, not a single snapshot

# A pick freezes this long before first pitch (mirrors main.LOCK_LEAD;
# defined here because main imports this module). Book readings after it
# are not evidence the pick could have used.
LOCK_LEAD = dt.timedelta(minutes=15)
IMBALANCE_MIN = 0.20   # resting-size lean that counts as confirmation

# BOOK GATE: REMOVED 2026-09-29. Five independent measurements put it at zero.
#
#   gate_sweep     standing alone on 958 games, worth +1.3 points
#   venue_swap     -1.4 on Polymarket, -9.5 on Kalshi's far better prices,
#                  best of five variants below what noise produces, p = 0.915
#   disagreement   sign reversed once the look-ahead was fixed: confirming
#                  -11.1%, not confirming +6.7%
#   venue_cross    "both venues confirm the money side" backs at -10.5%
#   gate_removal   the games it rejects return +7.3% (n=104), i.e. not losing
#
# Feeding it prices five to eleven times more accurate made it WORSE, which is
# what rules out "mis-fed" and leaves "empty". Measured against the book's own
# de-vigged price, Kalshi sits 0.007 out where the venues agree and 0.018 where
# they diverge; Polymarket 0.038 and 0.206.
#
# What the removal is and is not justified by (gate_removal.md):
#
#                       live        confirm dropped   book dropped
#   all months      +5.5% (104)      +4.3% (168)      +6.4% (208)
#   excluding Aug   +1.0%  (54)      +2.2%  (94)      +6.4% (132)
#   September       +2.7%  (37)      +1.3%  (60)      -0.4%  (61)
#   blocks won         -              4/8               4/8
#
# No ROI improvement is demonstrated - every interval overlaps and the blocks
# split evenly. What IS demonstrated is that the gate discards half the picks
# for nothing. More bets at the same edge is more edge in units, and a parameter
# measured at zero is overfitting surface. That is the whole case.
#
# The read requirement goes with it. It existed only to feed the confirmation
# check, so keeping it would reject games purely because a market was not
# logged - a cost with no remaining rationale. Set REQUIRE_BOOK_READ back to
# True to keep the read without the confirmation.
REQUIRE_BOOK_CONFIRM = False
REQUIRE_BOOK_READ = False

# CONFIRMATION: EITHER signal. Reverted 2026-09-21, the same day it was changed,
# because the change did not survive the test it should have been given first.
#
# The tightening (require BOTH the drift and the size lean, and loosen the line
# gate to 0.5% to give the volume back) was chosen on data that includes August,
# and August was the hot month. The holdout it was validated against begins
# 2026-07-23, so August sits INSIDE it - a holdout that contains the month you
# are worried about does not answer the worry. Run month by month
# (`src/change_check.py`, output/change_check.md):
#
# The figures below were RESTATED on 2026-09-29. The originals were computed
# through an uncut book_metrics, which read the whole day file including
# post-settlement prices, so every gate decision in them was partly set by the
# result. Corrected (backing the drift was +9.9% uncut against -5.0% cut, on the
# same 714 games), the numbers are smaller and the conclusion is unchanged:
#
#                   old: EITHER / >=1.0%        new: BOTH / >=0.5%
#   2026-07           9-8   (17)   -2.6%         8-6   (14)   +7.5%
#   2026-08          32-18  (50)  +10.4%        24-12  (36)  +19.9%
#   2026-09          22-15  (37)   +2.7%        18-17  (35)   -8.9%
#   all             63-41  (104)   +5.5%        50-35  (85)   +6.0%
#   excluding Aug   31-23   (54)   +1.0%        26-23  (49)   -4.2%
#
# The change is worth +0.5 points overall and -5.2 outside August, so the
# improvement was the hot month. The old setting is also the more consistent of
# the two: -2.6 / +10.4 / +2.7 across three months against +7.5 / +19.9 / -8.9,
# and it carries 104 picks against 85.
#
# Note what the correction cost: this rule's backtested edge was +17.6% and is
# +5.5%. Twelve of those points were look-ahead. The live record (-1.41% over
# 273 bets) was never the anomaly it looked like against +17.6%.
#
# The near_miss finding that motivated the change is not withdrawn - games
# failing only the book gate really did return -12.6%, stable across halves.
# What is withdrawn is the conclusion that tightening the gate on that basis
# improves the rule. It does not, outside the month it was measured in.
REQUIRE_BOTH_CONFIRMATIONS = False

# PRICE-DISCOUNT FILTER (added 2026-07-29, user's call, knowingly on thin data).
# The money side wins ~62% whether or not the line moves with it - what changes
# is the PRICE. When the line moves AWAY from the money, the same 62% is bought
# at a discount, and ROI went +1.9% -> +17.3% (n=55, holdout +9.8%, p=0.043).
# Caveats that were stated and accepted: ~20 configurations were scanned, so that
# p-value does not survive a multiple-comparisons correction, and the bootstrap
# CI (-10.7% to +44.0%) includes zero. Set REQUIRE_LINE_AGAINST = False to revert
# to plain consensus; the line tag is recorded either way so both buckets stay
# measurable from the snapshots.
LINE_MOVE_MIN = 0.01       # back to 0.01 with the book gate (measured as a pair)
REQUIRE_LINE_AGAINST = True


def line_tag(result: dict, team: str) -> str:
    """How the line moved relative to `team`: 'against' (price drifted away from
    it, so we buy at a discount), 'with' (price shortened on it), or 'flat'.

    line_check.implied_shift is signed toward the ADVANTAGE side, so it is
    flipped when the team we are backing is the other one."""
    pc = result.get("pick_criteria") or {}
    shift = (pc.get("line_check") or {}).get("implied_shift")
    if not isinstance(shift, (int, float)):
        return "flat"
    toward = shift if team == pc.get("advantage_team") else -shift
    if toward <= -LINE_MOVE_MIN:
        return "against"
    if toward >= LINE_MOVE_MIN:
        return "with"
    return "flat"


def _freeze_ts(game: dict) -> float | None:
    """When this game's book stops being evidence: first pitch minus LOCK_LEAD,
    the moment the board locks its pick. None if the start time is unusable."""
    start = game.get("game_datetime")
    if not isinstance(start, str):
        return None
    try:
        return (dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
                - LOCK_LEAD).timestamp()
    except ValueError:
        return None


def book_metrics(date: str) -> dict:
    """{game_pk: {"drift", "imbalance"}} for the advantage side's token, from the
    day's order-book log, using only readings from BEFORE the pick locks.

    The cut is what makes this honest. Live it changes nothing - a board built
    at 4pm reads a file that only holds readings up to 4pm. A BACKTEST reads
    the completed file, which logs straight through the game and past
    settlement, so an uncut `reads[-1]` is often a dead market at 0.00 or 1.00.
    Drift then reports which team won rather than where the money went, and
    every gate built on it scores itself on the answer. Measured: backing the
    drift was +9.9% uncut and -5.0% cut, on the same 714 games.

    {} when the log doesn't exist yet.
    """
    try:
        day = pm_books.load_day(date) or {}
    except Exception as exc:
        log.warning("pm book load failed (%s): %s", date, exc)
        return {}
    out: dict = {}
    for pk_s, g in (day.get("games") or {}).items():
        cutoff = _freeze_ts(g)
        reads = []
        for r in g.get("readings") or []:
            if r.get("empty"):
                continue
            b, a, t = r.get("bid"), r.get("ask"), r.get("t")
            if cutoff is not None and (not isinstance(t, (int, float)) or t > cutoff):
                continue
            if (isinstance(b, (int, float)) and isinstance(a, (int, float))
                    and a > b and (a - b) <= MAX_SPREAD):
                reads.append(r)
        if len(reads) < MIN_READINGS:
            continue
        reads.sort(key=lambda r: r.get("t", 0))
        first, last = reads[0], reads[-1]
        drift = (last["bid"] + last["ask"]) / 2 - (first["bid"] + first["ask"]) / 2
        bs, as_ = last.get("bid_sz") or 0, last.get("ask_sz") or 0
        imb = (bs - as_) / (bs + as_) if (bs + as_) > 0 else 0.0
        try:
            out[int(pk_s)] = {"drift": round(drift, 4), "imbalance": round(imb, 3)}
        except (TypeError, ValueError):
            continue
    return out


def _confirms(m: dict, consensus_is_adv: bool) -> bool:
    """Does the order book lean toward the consensus side? The log is written
    from the ADVANTAGE side's token, so invert when consensus is the other team."""
    drift_ok, size_ok = m["drift"] > 0, m["imbalance"] > IMBALANCE_MIN
    toward_adv = (drift_ok and size_ok) if REQUIRE_BOTH_CONFIRMATIONS else (drift_ok or size_ok)
    return toward_adv if consensus_is_adv else (not toward_adv)


def evaluate(result: dict, metrics: dict) -> dict | None:
    """The consensus play for one evaluated game, or None.

    Returns {"bet", "odds", "reason", "drift", "imbalance"}. `metrics` is the
    output of book_metrics() for the slate."""
    pc = result.get("pick_criteria") or {}
    chk = result.get("public_check") or {}
    maj = (result.get("public_majority") or {}).get("team")
    matchup = result.get("matchup") or ""
    if chk.get("money") != "with public" or not maj or " @ " not in matchup:
        return None                      # no handle/ticket agreement -> no play
    adv = pc.get("advantage_team")
    away, home = matchup.split(" @ ")
    if maj not in (away, home) or not adv:
        return None
    # price for the consensus side, from whichever slot it occupies
    odds = (pc.get("advantage_moneyline") if maj == adv
            else pc.get("opponent_moneyline"))
    if not isinstance(odds, int):
        return None
    m = metrics.get(result.get("game_pk"))
    if REQUIRE_BOOK_READ and not m:
        return None                      # no order-book read yet -> no play
    if REQUIRE_BOOK_CONFIRM and (not m or not _confirms(m, maj == adv)):
        return None
    tag = line_tag(result, maj)
    if REQUIRE_LINE_AGAINST and tag != "against":
        return None                      # no price discount -> no play
    reason = ("handle+tickets agree, line moved against us"
              if not REQUIRE_BOOK_CONFIRM else
              "handle+tickets agree, order book confirms, line moved against us")
    # drift/imbalance are display-only now; None when no market was logged
    return {"bet": maj, "odds": odds, "reason": reason,
            "drift": m["drift"] if m else None,
            "imbalance": m["imbalance"] if m else None, "line": tag}


def reject_reason(result: dict, metrics: dict) -> str:
    """Why this game is not a play - checked in the same order as evaluate()."""
    pc = result.get("pick_criteria") or {}
    chk = result.get("public_check") or {}
    maj = (result.get("public_majority") or {}).get("team")
    if chk.get("money") != "with public":
        return f"no handle/ticket agreement ({chk.get('money') or 'no money read'}) — no play"
    if not maj:
        return "no public majority read — no play"
    m = metrics.get(result.get("game_pk"))
    if REQUIRE_BOOK_READ and not m:
        return "no pre-game order-book read yet — no play"
    adv = pc.get("advantage_team")
    if REQUIRE_BOOK_CONFIRM and (not m or not _confirms(m, maj == adv)):
        return "order book does not confirm the consensus side — no play"
    if REQUIRE_LINE_AGAINST:
        tag = line_tag(result, maj)
        if tag != "against":
            return (f"line moved {tag} the money — no price discount, no play")
    return "no play"
