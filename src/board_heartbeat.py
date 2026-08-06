"""
Independent safety net for the board going stale.

WHAT WENT WRONG
On 2026-08-06 the board stopped rebuilding at ~11:23Z and nothing posted to
Telegram for six hours. Two failures stacked: GitHub silently dropped the 16:00
and 17:00 scheduled kicks, and when a delayed kick finally fired it cancelled a
manual run and then stuck in the queue. Nothing errored, nothing alerted - the
board just quietly stopped.

WHY THIS IS A SEPARATE WORKFLOW, NOT A FIX TO THAT ONE
The refresh loop cannot detect its own absence. Anything that depends on the
same cron firing shares the same failure. So this runs on its own schedule,
offset half an hour, and REBUILDS THE BOARD ITSELF rather than trying to
re-trigger the other workflow - a workflow_dispatch sent with GITHUB_TOKEN
deliberately does not start a new run, so that route would fail silently too,
which is the exact class of bug being fixed.

WHAT IT DOES
Inside the active window, if today's board is missing or older than
STALE_MINUTES, it rebuilds and posts. Otherwise it does nothing and says so. If
the rebuild itself fails, it sends a Telegram alert and exits non-zero - a stale
board should never again be invisible.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import notify, pregame

log = logging.getLogger("heartbeat")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

STALE_MINUTES = 75          # the board posts hourly; 75 leaves grace for a slow run
WINDOW_START_H = 12         # noon ET - matches the refresh workflow's first kick
WINDOW_END_H = 1            # 1am ET the next morning


def in_window(now: dt.datetime) -> bool:
    """Active hours: noon ET through 1am ET."""
    return now.hour >= WINDOW_START_H or now.hour < WINDOW_END_H


def board_age_minutes(date: str, now: dt.datetime) -> float | None:
    """Minutes since today's board was generated. None if there is no board."""
    p = OUTPUT_DIR / f"picks_{date}.json"
    try:
        gen = json.loads(p.read_text()).get("generated_at")
    except (OSError, ValueError):
        return None
    try:
        ts = dt.datetime.fromisoformat(str(gen).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return (now - ts).total_seconds() / 60.0


def run() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    et = now.astimezone(EASTERN)
    date = et.date().isoformat()

    if not in_window(et):
        log.info("outside the active window (%s ET) - nothing to do", et.strftime("%H:%M"))
        return 0

    age = board_age_minutes(date, now)
    if age is None:
        log.warning("no board for %s - rebuilding", date)
    elif age > STALE_MINUTES:
        log.warning("board for %s is %.0f min old (limit %d) - rebuilding",
                    date, age, STALE_MINUTES)
    else:
        log.info("board for %s is %.0f min old - healthy, nothing to do", date, age)
        return 0

    try:
        pregame.run(force_telegram=True)
    except Exception as exc:
        log.error("heartbeat rebuild FAILED: %s", exc)
        # the original bug was silence, so make this one audible
        try:
            notify.send_telegram(
                "⚠️ Board heartbeat: today's board is stale and the rebuild "
                f"failed ({type(exc).__name__}). No picks are being posted.")
        except Exception:
            log.error("could not send the heartbeat alert either")
        return 1
    log.info("heartbeat rebuilt and posted the board for %s", date)
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    raise SystemExit(run())


if __name__ == "__main__":
    main()
