"""
Pre-game refresh: ~30 minutes before each distinct game start, regenerate picks
once (so they use confirmed lineups + latest lines) and send fresh results to
Telegram.

GitHub Actions can't fire at arbitrary per-game times, so a workflow polls this
every ~15 min during game hours. Each run:
  - reads today's schedule and groups games by first-pitch time (a "slot");
  - finds slots starting in ~15-45 min that haven't been handled yet;
  - if any are due, regenerates the day's picks ONCE (covering every game at
    those slots - simultaneous starts are one slot, so no double run);
  - records handled slots in output/pregame_state_<date>.json so later polls in
    the same window don't repeat them;
  - Telegrams the picks only when the pick set changed from what's committed.

Grading/auto-tuning still happen in the morning daily run; this only refreshes.
"""

from __future__ import annotations

import datetime as dt
import json
import logging

from . import grade, main as picks_main, notify
from .mlb_api import SPORT_ID, _get

log = logging.getLogger("pregame")

OUTPUT_DIR = picks_main.OUTPUT_DIR
# GitHub throttles the */15 cron hard (observed firings ~2h apart), so a narrow
# "T-15" window would straddle the gaps and miss slots entirely. Instead: refresh
# any unhandled slot starting within DUE_HORIZON, but only mark it handled once a
# refresh lands within FINAL_MIN of first pitch - so every slot gets a refresh as
# close to T-15 as the platform's sparse firing allows (often twice: an early one
# and a final one).
DUE_HORIZON = 90   # minutes ahead: refresh anything unhandled starting inside this
FINAL_MIN = 30     # a refresh this close to start is the final word for that slot


def schedule_slots(date: str) -> dict[str, list[int]]:
    """{first_pitch_iso_utc: [game_pk, ...]} for the date. Simultaneous games
    share a slot key, so they're handled together (one run)."""
    data = _get("schedule", sportId=SPORT_ID, date=date)
    slots: dict[str, list[int]] = {}
    for day in data.get("dates", []):
        for g in day.get("games", []):
            iso = g.get("gameDate")
            if iso:
                slots.setdefault(iso, []).append(g.get("gamePk"))
    return slots


def due_slots(slots: dict, now: dt.datetime, processed: set[str]) -> dict[str, list[int]]:
    """Unhandled slots starting within DUE_HORIZON minutes."""
    due: dict[str, list[int]] = {}
    for iso, pks in slots.items():
        try:
            start = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError:
            continue
        minutes = (start - now).total_seconds() / 60.0
        if 0 < minutes <= DUE_HORIZON and iso not in processed:
            due[iso] = pks
    return due


def run() -> bool:
    date = picks_main.today_eastern()
    now = dt.datetime.now(dt.timezone.utc)
    state_path = OUTPUT_DIR / f"pregame_state_{date}.json"
    processed: set[str] = set()
    if state_path.exists():
        try:
            processed = set(json.loads(state_path.read_text()))
        except ValueError:
            pass

    try:
        slots = schedule_slots(date)
    except Exception as exc:
        log.warning("schedule fetch failed: %s", exc)
        return False

    # `processed` = slots we've already sent a pre-game board for. A slot is due
    # once it's inside DUE_HORIZON and not yet pinged - so every slot gets exactly
    # one refresh+ping at the first poll that catches it within the window, which
    # (given GitHub's ~2h cron throttling) is the only reliable moment. We do NOT
    # wait for a tight FINAL_MIN window: a poll almost never lands in it, so slots
    # would slip past first pitch un-pinged.
    due = due_slots(slots, now, processed)
    if not due:
        log.info("no un-pinged game slot in the next ~%d min (%s)", DUE_HORIZON, date)
        return False
    log.info("pre-game slots due: %s (%d game(s))", sorted(due), sum(len(v) for v in due.values()))

    # remember the currently committed picks (+ coin-flip plays) to detect changes
    old_picks = None
    pf = OUTPUT_DIR / f"picks_{date}.json"
    if pf.exists():
        try:
            prev = json.loads(pf.read_text())
            old_picks = (prev.get("picks"), prev.get("coin_flips"))
        except ValueError:
            pass

    payload = picks_main.run(date)
    picks_main.write_outputs(payload, date)
    grade.update_ledger(date)  # move any now-final games into the record

    # mark every due slot pinged so later (throttled) polls don't re-send it
    processed |= set(due)
    OUTPUT_DIR.mkdir(exist_ok=True)
    state_path.write_text(json.dumps(sorted(processed)))

    # one guaranteed board per slot; if the nearest slot is inside FINAL_MIN the
    # lineups/odds are locked, otherwise it's an earlier heads-up.
    soonest = min((dt.datetime.fromisoformat(iso.replace("Z", "+00:00")) - now).total_seconds() / 60.0
                  for iso in due)
    changed = (payload.get("picks"), payload.get("coin_flips")) != old_picks
    if soonest <= FINAL_MIN:
        head = "🔔 first pitch soon — board locked in:\n\n"
    else:
        head = f"⏳ pre-game heads-up (~{int(soonest)} min to first pitch):\n\n"
    notify.send_telegram(head + picks_main.telegram_text(payload))
    log.info("telegram sent (%s; soonest %d min)",
             "picks changed" if changed else "scheduled ping", int(soonest))
    return True


def main() -> None:
    run()


if __name__ == "__main__":
    main()
