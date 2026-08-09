"""
Operator-entered picks that survive a board rebuild.

WHY THIS EXISTS
The board is stateless - every refresh regenerates picks_<date>.json from
scratch - so a hand-edited pick is wiped within the hour. Anything entered by
hand has to live in its own file and be re-applied on every rebuild.

WHAT IT IS FOR
A pick made on the operator's judgement rather than the consensus rule. It lands
in the SAME record, at the operator's instruction, so the all-time number stays
one number rather than fragmenting into rules nobody can reconcile later.

WHAT IT COSTS, stated once here so it is not forgotten
These picks did NOT come from the consensus rule, and mixing them into the same
ledger means the consensus rule's own record can no longer be read off the
all-time figure. Every entry therefore carries `source: "manual"` and its own
reason, so the two populations remain separable in analysis even though they
share a ledger. Any future backtest of the consensus rule must filter these out
or it will be measuring a blend.

output/manual_picks_<date>.json:
  {"date": ..., "picks": [{game_pk, bet_team, bet_moneyline, reason, added_at}]}

Applying is idempotent: re-running on an already-marked board changes nothing.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

log = logging.getLogger("manual_picks")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def path_for(date: str) -> Path:
    return OUTPUT_DIR / f"manual_picks_{date}.json"


def load(date: str) -> list[dict]:
    try:
        return json.loads(path_for(date).read_text()).get("picks") or []
    except (OSError, ValueError):
        return []


def add(date: str, game_pk: int, bet_team: str, bet_moneyline: int,
        reason: str) -> dict:
    """Record a manual pick. Replaces any existing entry for the same game."""
    picks = [p for p in load(date) if p.get("game_pk") != game_pk]
    entry = {
        "game_pk": game_pk, "bet_team": bet_team,
        "bet_moneyline": bet_moneyline, "reason": reason,
        "added_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    picks.append(entry)
    OUTPUT_DIR.mkdir(exist_ok=True)
    path_for(date).write_text(json.dumps({"date": date, "picks": picks}, indent=1))
    log.info("manual pick recorded: %s %s (%s)", bet_team, bet_moneyline, reason)
    return entry


def apply(results: list[dict], date: str) -> int:
    """Mark manual picks on a freshly built board. Returns how many applied.

    Runs AFTER the consensus pass so it is the last word: a game the rule
    already picked keeps the rule's own reasoning unless a manual entry names
    the same game, in which case the operator's choice wins."""
    entries = {p.get("game_pk"): p for p in load(date)}
    if not entries:
        return 0
    applied = 0
    for r in results:
        e = entries.get(r.get("game_pk"))
        if not e:
            continue
        pc = r.setdefault("pick_criteria", {})
        pc["play"] = "pick"
        pc["status"] = "PICK"
        pc["bet_team"] = e["bet_team"]
        pc["bet_moneyline"] = e["bet_moneyline"]
        pc["reason"] = e["reason"]
        # the flag that keeps the two populations separable in a shared ledger
        pc["source"] = "manual"
        applied += 1
    if applied:
        log.info("applied %d manual pick(s) for %s", applied, date)
    missing = set(entries) - {r.get("game_pk") for r in results}
    if missing:
        log.warning("manual picks reference games not on the board: %s", missing)
    return applied
