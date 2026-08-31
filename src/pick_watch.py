"""
Tell the channel when a pick is WITHDRAWN, not just when one appears.

THE GAP THIS CLOSES
The board is a live read, not a locked slate. Every refresh re-evaluates from
scratch, so a game that qualifies at 11am can stop qualifying by 6pm - the order
book flips, or the line moves back and the price discount is gone. That is the
rule working correctly, and the audit says the withdrawals earn their keep:
picks that stopped qualifying before their lock returned -12.9% over 155 games,
against +0.7% for the ones that survived.

The problem is not the withdrawal. It is that NOTHING ANNOUNCES IT.

A new pick gets a board post. A withdrawn pick gets silence, and silence is
indistinguishable from "the board has not refreshed yet" - which is the common
case, because GitHub drops most scheduled runs. The heartbeat has been firing at
roughly a fifth of its schedule and the board went seven hours without a refresh
on 2026-08-29. So the realistic failure is: a pick is posted in the morning,
withdrawn at 4pm, no board reaches the channel in between, and the bet is placed
on a recommendation the rule had already abandoned.

WHAT IT DOES
Remembers which games have been announced as picks for a date, and on every
rebuild reports any that are no longer picks while the game has NOT yet started.
After first pitch the game is locked and cannot change, so an alert there is
noise.

Also announces a SIDE FLIP - same game, other team - which is rarer and worse
than a plain withdrawal, since acting on the stale post now means holding the
opposite of what the rule says.

State lives in output/posted_picks_<date>.json, keyed by game_pk, so a rebuild
that crashes or a missed cron cannot cause a duplicate alert.

Fails soft at every step: an alert that cannot be sent must never take the board
down with it.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

from . import notify

log = logging.getLogger("pick_watch")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def path_for(date: str) -> Path:
    return OUTPUT_DIR / f"posted_picks_{date}.json"


def load(date: str) -> dict:
    try:
        return json.loads(path_for(date).read_text()).get("picks") or {}
    except (OSError, ValueError):
        return {}


def save(date: str, picks: dict) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path_for(date).write_text(
        json.dumps({"date": date, "picks": picks}, indent=1))


def _started(g: dict, now: dt.datetime) -> bool:
    s = g.get("game_datetime")
    if not s:
        return False
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")) <= now
    except ValueError:
        return False


def check(results: list[dict], date: str, send=None) -> list[str]:
    """Compare this build's picks against what has been announced.

    Returns the alert lines sent (empty when nothing changed). Call AFTER the
    lock and after any manual/road-trip picks are applied, so it sees the board
    exactly as the channel will."""
    send = send or notify.send_telegram
    now = dt.datetime.now(dt.timezone.utc)
    known = load(date)
    alerts: list[str] = []
    current: dict = {}

    by_pk = {}
    for r in results:
        pk = str(r.get("game_pk"))
        by_pk[pk] = r
        pc = r.get("pick_criteria") or {}
        if pc.get("play") == "pick" and pc.get("bet_team"):
            current[pk] = {"bet": pc["bet_team"],
                           "odds": pc.get("bet_moneyline"),
                           "matchup": r.get("matchup")}

    for pk, was in known.items():
        now_pick = current.get(pk)
        g = by_pk.get(pk)
        # a game we can no longer see, or one already under way, is not news:
        # after first pitch the lock freezes it and nothing can change
        if g is None or _started(g, now):
            continue
        if now_pick is None:
            if was.get("withdrawn"):
                continue          # already announced; do not re-fire every hour
            alerts.append(
                f"❌ WITHDRAWN — {was.get('matchup')}\n"
                f"{was.get('bet')} {was.get('odds'):+d} is no longer a play. "
                "The rule re-evaluated and it no longer qualifies.")
        elif now_pick["bet"] != was.get("bet"):
            alerts.append(
                f"🔄 SIDE FLIPPED — {was.get('matchup')}\n"
                f"was {was.get('bet')} {was.get('odds'):+d}, now "
                f"{now_pick['bet']} {now_pick['odds']:+d}.")

    # Keep withdrawn picks in the file, flagged, so the alert fires ONCE. The
    # first version re-announced every withdrawal on every rebuild - hourly spam
    # that teaches the channel to ignore the one alert that matters. If the game
    # qualifies again later, `current` overwrites the flag and a fresh
    # withdrawal is genuinely new news.
    merged = dict(known)
    for pk, was in known.items():
        if pk not in current and any(was.get("matchup") and was["matchup"] in a
                                     for a in alerts):
            merged[pk] = {**was, "withdrawn": True}
    merged.update(current)
    save(date, merged)

    for a in alerts:
        try:
            send(a)
        except Exception as exc:
            log.error("withdrawal alert failed: %s", exc)
    if alerts:
        log.info("pick_watch: %d change alert(s) for %s", len(alerts), date)
    return alerts
