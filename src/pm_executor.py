"""
DRY-RUN Polymarket executor: phantom orders on every board PLAY.

The enter-only auto-bettor, minus the wallet. At each poll tick (piggybacking
the pm_books cadence) it:

  1. places a phantom LIMIT BUY on a play's side the moment the pick LOCKS
     (15 min before first pitch), priced at the book-implied probability plus a
     small pad - the bot never chases a thin book upward;
  2. fills the order only if the REAL recorded ask (from pm_books' order-book
     readings) comes at/under the limit BEFORE first pitch - so fills are
     honest, not assumed;
  3. cancels anything unfilled shortly after first pitch (an unfilled order =
     the liquidity wasn't there - exactly the go/no-go signal this dry run
     exists to measure);
  4. settles fills against real MLB finals into output/pm_paper.json - the
     paper ledger. $1 stake per position: win pays 1/fill - 1 MINUS the
     platform fee (FEE_RATE of gross winnings, conservative until the US
     entity's real schedule is known), loss loses 1. Gross, fee, and net are
     all stored per position.

Completely separate from the channel record (which stays graded at book
moneylines) and sends nothing to Telegram - it's a silent rehearsal. When the
paper ledger and the liquidity data justify it, the same logic gets keys, a
VPS, and real (tiny) stakes.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import time
import zoneinfo
from pathlib import Path

from . import grade, mlb_api, pm_books

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pm_executor")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
STATE_PATH = OUTPUT_DIR / "pm_paper.json"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

STAKE = 1.0
LIMIT_PAD = 0.02        # pay at most book-implied + 2 pts - never chase
CANCEL_AFTER = 600      # unfilled 10 min after first pitch -> cancelled
LOCK_LEAD = 15 * 60
# Platform fee, taken from WINNINGS at settlement. Polymarket historically
# charged ~0% on game markets, but the US entity's schedule is unverified -
# so the paper ledger books a conservative 2% of gross winnings by default
# (override with PM_FEE_RATE once the real schedule is known from a live
# account). Gross and fee are both stored, so re-costing later is arithmetic,
# not a re-run.
import os as _os
FEE_RATE = float(_os.environ.get("PM_FEE_RATE", "0.02"))


def _implied(ml) -> float:
    ml = int(ml)
    return 100.0 / (ml + 100) if ml > 0 else -ml / (-ml + 100.0)


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text())
    except (OSError, ValueError):
        return {"mode": "dry-run", "bankroll": 0.0, "positions": {}}


def save_state(state: dict) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=1))


def _latest_ask(day_books: dict, pk: str, before_ts: int) -> dict | None:
    """The freshest pm_books reading with an ask for a game at/before before_ts."""
    entry = (day_books.get("games") or {}).get(pk)
    for r in reversed((entry or {}).get("readings") or []):
        if r.get("ask") is not None and r["t"] <= before_ts:
            return r
    return None


def run(date: str | None = None, now_ts: int | None = None) -> dict:
    date = date or dt.datetime.now(EASTERN).date().isoformat()
    now = now_ts or int(time.time())
    state = load_state()
    positions = state["positions"]

    picks_path = OUTPUT_DIR / f"picks_{date}.json"
    games = []
    if picks_path.exists():
        games = json.loads(picks_path.read_text()).get("games", [])
    day_books = pm_books.load_day(date)

    # 1+2+3: place / fill / cancel today's phantom orders
    for g in games:
        pc = g.get("pick_criteria") or {}
        if grade._play(g) != "pick" or not pc.get("advantage_team"):
            continue
        pk = str(g.get("game_pk"))
        key = f"{date}#{pk}"
        try:
            start_ts = int(dt.datetime.fromisoformat(
                str(g.get("game_datetime", "")).replace("Z", "+00:00")).timestamp())
        except Exception:
            continue
        pos = positions.get(key)
        if pos is None:
            if not (start_ts - LOCK_LEAD <= now <= start_ts + CANCEL_AFTER):
                continue
            ml = pc.get("advantage_moneyline")
            if ml is None:
                continue
            ref = _implied(ml)
            pos = {"date": date, "matchup": g["matchup"], "side": pc["advantage_team"],
                   "stake": STAKE, "ref": round(ref, 3),
                   "limit": round(ref + LIMIT_PAD, 3),
                   "placed_t": now, "state": "OPEN"}
            positions[key] = pos
            log.info("phantom order: %s @ limit %.2f (%s)", pos["side"], pos["limit"], key)
        if pos["state"] == "OPEN":
            # fills only on a real pre-game ask at/under the limit
            r = _latest_ask(day_books, pk, before_ts=start_ts)
            if r and r["t"] >= pos["placed_t"] - 900 and r["ask"] <= pos["limit"]:
                pos.update(state="FILLED", fill=r["ask"], fill_t=r["t"],
                           fill_sz=r.get("ask_sz"))
                log.info("phantom FILL: %s @ %.2f (%s)", pos["side"], pos["fill"], key)
            elif now > start_ts + CANCEL_AFTER:
                pos["state"] = "CANCELLED"   # the liquidity wasn't there
                log.info("phantom order cancelled unfilled (%s)", key)

    # 4: settle any filled position whose game has gone final
    results_cache: dict = {}
    for key, pos in positions.items():
        if pos["state"] != "FILLED":
            continue
        d = pos["date"]
        if d not in results_cache:
            try:
                results_cache[d] = mlb_api.results_for(d)
            except Exception as exc:
                log.warning("results unavailable for %s: %s", d, exc)
                results_cache[d] = {}
        pk = key.rsplit("#", 1)[1]
        res = None
        for rpk, r in results_cache[d].items():
            if str(rpk) == pk:
                res = r
                break
        if not res or not res.get("final") or not res.get("winner"):
            continue
        won = res["winner"] == pos["side"]
        gross = round((1.0 / pos["fill"] - 1.0) if won else -1.0, 3)
        fee = round(FEE_RATE * gross, 3) if won else 0.0   # fees come off winnings
        net = round(gross - fee, 3)
        pos.update(state="SETTLED", won=won, profit_gross=gross, fee=fee, profit=net)
        state["fee_rate"] = FEE_RATE
        state["bankroll"] = round(state["bankroll"] + net, 3)
        log.info("settled %s: %s gross %+0.3f fee %0.3f net %+0.3f (bankroll %+0.3f)",
                 key, "WON" if won else "LOST", gross, fee, net, state["bankroll"])

    save_state(state)
    counts: dict = {}
    for p in positions.values():
        counts[p["state"]] = counts.get(p["state"], 0) + 1
    log.info("paper book: %s | bankroll %+0.3f", counts or "empty", state["bankroll"])
    return state


def main() -> None:
    run()


if __name__ == "__main__":
    main()
