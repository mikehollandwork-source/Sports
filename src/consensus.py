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

import logging

from . import pm_books

log = logging.getLogger("consensus")

MAX_SPREAD = 0.15      # wider than this is not a real two-sided market
MIN_READINGS = 2       # need a run-up, not a single snapshot
IMBALANCE_MIN = 0.20   # resting-size lean that counts as confirmation

# PRICE-DISCOUNT FILTER (added 2026-07-29, user's call, knowingly on thin data).
# The money side wins ~62% whether or not the line moves with it - what changes
# is the PRICE. When the line moves AWAY from the money, the same 62% is bought
# at a discount, and ROI went +1.9% -> +17.3% (n=55, holdout +9.8%, p=0.043).
# Caveats that were stated and accepted: ~20 configurations were scanned, so that
# p-value does not survive a multiple-comparisons correction, and the bootstrap
# CI (-10.7% to +44.0%) includes zero. Set REQUIRE_LINE_AGAINST = False to revert
# to plain consensus; the line tag is recorded either way so both buckets stay
# measurable from the snapshots.
LINE_MOVE_MIN = 0.01       # implied-probability move that counts as a real move
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


def book_metrics(date: str) -> dict:
    """{game_pk: {"drift", "imbalance"}} for the advantage side's token, from the
    day's pre-game order-book log. {} when the log doesn't exist yet."""
    try:
        day = pm_books.load_day(date) or {}
    except Exception as exc:
        log.warning("pm book load failed (%s): %s", date, exc)
        return {}
    out: dict = {}
    for pk_s, g in (day.get("games") or {}).items():
        reads = []
        for r in g.get("readings") or []:
            if r.get("empty"):
                continue
            b, a = r.get("bid"), r.get("ask")
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
    toward_adv = m["drift"] > 0 or m["imbalance"] > IMBALANCE_MIN
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
    if not m:
        return None                      # no order-book read yet -> no play
    if not _confirms(m, maj == adv):
        return None
    tag = line_tag(result, maj)
    if REQUIRE_LINE_AGAINST and tag != "against":
        return None                      # no price discount -> no play
    return {"bet": maj, "odds": odds,
            "reason": "handle+tickets agree, order book confirms, line moved against us",
            "drift": m["drift"], "imbalance": m["imbalance"], "line": tag}


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
    if not m:
        return "no pre-game order-book read yet — no play"
    adv = pc.get("advantage_team")
    if not _confirms(m, maj == adv):
        return "order book does not confirm the consensus side — no play"
    if REQUIRE_LINE_AGAINST:
        tag = line_tag(result, maj)
        if tag != "against":
            return (f"line moved {tag} the money — no price discount, no play")
    return "no play"
