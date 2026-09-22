"""
Back the other side when the rule withdraws a pick. Added at the user's call.

WHAT THE EVIDENCE ACTUALLY SAYS, recorded before this goes live
Withdrawn picks returned -14.7% over 196 games; fading them returned +12.8%.
That looks like an edge and it has not cleared any bar:

    day-block 95% CI on the fade      -3.6% to +29.3%   (includes zero)
    best of 4 withdrawal reasons      p = 0.984
    best of 20 reason x price cells   p = 0.901
    combined back+fade                -1.9%  (the vig, paid on both sides)

The hit rate is 101-95. That is 51.5% - the return comes from those wins landing
on longer prices, not from winning more often. A dozen games either way moves it
several points.

WHY POOLED AND NOT THE BEST CELL
Because pooling selects nothing, so there is nothing to be wrong about. Both
slicings were tested and neither found a pocket: the best reason and the best
reason-by-price cell each came in FAR below what their own grids manufacture
from noise. Shipping the greenest box out of twenty is the move that has failed
sixteen times in this repo; shipping the pooled average is not.

HOW IT WORKS
When a game that was announced as a pick stops qualifying, and it has not yet
started, the opposite side is added at its own current price, tagged
source="fade". The rule's own withdrawal is the trigger - no new signal, no new
threshold, nothing to tune.

It relies on posted_picks_<date>.json, which pick_watch maintains. A pick has to
have been ANNOUNCED first; a game that never qualified is not a fade.

Entries carry source="fade" so the consensus rule's own record stays readable
separately from this. Set ENABLED = False to turn it off; nothing else changes.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

log = logging.getLogger("fade_rule")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

ENABLED = True


def _started(g: dict, now: dt.datetime) -> bool:
    s = g.get("game_datetime")
    if not s:
        return False
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")) <= now
    except ValueError:
        return False


def _other_side(g: dict, bet: str) -> tuple[str, int] | None:
    """The opposite team and ITS price. Fading is not the same bet reversed -
    it pays the other side's own vig, which is why the two do not sum to zero."""
    m = g.get("matchup") or ""
    if " @ " not in m:
        return None
    away, home = m.split(" @ ")
    other = home if bet == away else away
    pc = g.get("pick_criteria") or {}
    adv = pc.get("advantage_team")
    odds = (pc.get("opponent_moneyline") if bet == adv
            else pc.get("advantage_moneyline"))
    return (other, odds) if isinstance(odds, int) else None


def _same_side(g: dict, bet: str) -> tuple[str, int] | None:
    """`bet` and ITS current price - used to re-assert a fade that is already
    standing, rather than flipping it."""
    m = g.get("matchup") or ""
    if " @ " not in m or bet not in m.split(" @ "):
        return None
    pc = g.get("pick_criteria") or {}
    adv = pc.get("advantage_team")
    odds = (pc.get("advantage_moneyline") if bet == adv
            else pc.get("opponent_moneyline"))
    return (bet, odds) if isinstance(odds, int) else None


def apply(results: list[dict], date: str) -> int:
    """Add a fade for every announced pick that no longer qualifies.

    Runs after the consensus, manual and road-trip passes, and never overwrites
    a game any of them picked - a game the rule is backing right now is not a
    game it withdrew."""
    if not ENABLED:
        return 0
    try:
        posted = json.loads(
            (OUTPUT_DIR / f"posted_picks_{date}.json").read_text()).get("picks") or {}
    except (OSError, ValueError):
        return 0
    if not posted:
        return 0

    now = dt.datetime.now(dt.timezone.utc)
    added = 0
    for r in results:
        pk = str(r.get("game_pk"))
        was = posted.get(pk)
        if not was:
            continue
        pc = r.setdefault("pick_criteria", {})
        if pc.get("play") == "pick":
            continue                      # still a play; nothing was withdrawn
        if _started(r, now):
            continue                      # locked: the fade was never available
        # A fade is triggered by the CONSENSUS rule withdrawing. If the posted
        # pick is itself a fade, taking "the other side" flips the bet back to
        # the team the rule withdrew - and because pick_watch then records THAT
        # as the posted pick, the game flips again an hour later, forever. On
        # 2026-09-22 one game was posted as Seattle -137, then Houston +120,
        # then Seattle -130: both sides of the same game, both into the record.
        # A standing fade is re-asserted at its current price instead.
        if was.get("source") == "fade":
            side = _same_side(r, was.get("bet"))
            if not side:
                continue
            team, odds = side
            pc.update({"play": "pick", "status": "PICK", "bet_team": team,
                       "bet_moneyline": odds, "source": "fade",
                       "reason": was.get("reason")
                       or f"fade — standing bet on {team}"})
            added += 1
            continue
        side = _other_side(r, was.get("bet"))
        if not side:
            continue
        other, odds = side
        pc.update({"play": "pick", "status": "PICK", "bet_team": other,
                   "bet_moneyline": odds, "source": "fade",
                   "reason": f"fade — {was.get('bet')} {was.get('odds'):+d} "
                             "was withdrawn"})
        added += 1
    if added:
        log.info("applied %d fade pick(s) for %s", added, date)
    return added
