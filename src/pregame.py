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
DUE_MIN, DUE_MAX = 10, 30   # fire when a slot is this many minutes away (~T-15;
                            # Actions cron is 15-min granular and often late, so
                            # this is as close to "15 min before" as it can aim)


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
    due: dict[str, list[int]] = {}
    for iso, pks in slots.items():
        try:
            start = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError:
            continue
        minutes = (start - now).total_seconds() / 60.0
        if DUE_MIN <= minutes <= DUE_MAX and iso not in processed:
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

    due = due_slots(slots, now, processed)
    if not due:
        log.info("no game slot due in the next ~30 min (%s)", date)
        return False
    log.info("pre-game slots due: %s (%d game(s))", sorted(due), sum(len(v) for v in due.values()))

    # remember the currently committed picks to detect changes
    old_picks = None
    pf = OUTPUT_DIR / f"picks_{date}.json"
    if pf.exists():
        try:
            old_picks = json.loads(pf.read_text()).get("picks")
        except ValueError:
            pass

    payload = picks_main.run(date)
    picks_main.write_outputs(payload, date)
    grade.update_ledger(date)  # move any now-final games into the record

    processed |= set(due)
    OUTPUT_DIR.mkdir(exist_ok=True)
    state_path.write_text(json.dumps(sorted(processed)))

    if payload.get("picks") != old_picks:
        notify.send_telegram(picks_main.telegram_text(payload))
        log.info("picks changed -> telegram sent")
    else:
        log.info("picks unchanged -> no telegram")
    return True


def main() -> None:
    run()


if __name__ == "__main__":
    main()
