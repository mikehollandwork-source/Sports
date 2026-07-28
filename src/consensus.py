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
    return {"bet": maj, "odds": odds,
            "reason": "handle+tickets agree, order book confirms",
            "drift": m["drift"], "imbalance": m["imbalance"]}
