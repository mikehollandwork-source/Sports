"""When should the board rebuild next?

THE PROBLEM
Each game freezes LOCK_LEAD (15 minutes) before its own first pitch, and
whatever the board says at that moment is the bet and the price that settle.
But the refresh loop sleeps to the top of the hour, so a game locks on
whatever the last hourly board computed - 20 to 55 minutes earlier, ~30 on
average across a normal slate. Every pick is therefore frozen on a stale read
of the order book and the line, which are the two inputs the rule is built on.

THE FIX
Wake shortly before the NEXT game locks, rather than only on the hour. One
wake covers every game locking in that minute, and the hourly wake stays as a
floor so a slate with no upcoming locks still refreshes.

This changes no rule and no threshold. It only means the data a pick is frozen
on is a couple of minutes old instead of half an hour.

Prints "<unix timestamp> <kind>", kind being `hour` or `lock`.

The kind matters because a lock wake should NOT re-post the whole board to
Telegram: that would put eight extra boards on the phone a night and make the
rule look like it is flip-flopping, when all that changed is that the data got
fresher. Lock wakes rebuild silently; the hourly wake posts the board. Pick
withdrawals and changes are announced either way, since `pick_watch` runs on
every rebuild - and a change found right before a game freezes is exactly the
one worth hearing about.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import zoneinfo
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

LOCK_LEAD = dt.timedelta(minutes=15)   # mirrors main.LOCK_LEAD
LEAD_IN = dt.timedelta(minutes=2)      # build the board just BEFORE the freeze
MIN_SLEEP = dt.timedelta(seconds=60)   # never spin


def next_wake(date: str, now: dt.datetime | None = None) -> tuple[int, str]:
    now = now or dt.datetime.now(dt.timezone.utc)
    floor = now + MIN_SLEEP
    top_of_hour = (now.replace(minute=0, second=0, microsecond=0)
                   + dt.timedelta(hours=1))
    best = top_of_hour

    try:
        games = json.loads(
            (OUTPUT_DIR / f"picks_{date}.json").read_text()).get("games", [])
    except (OSError, ValueError):
        return int(best.timestamp()), "hour"

    for g in games:
        s = g.get("game_datetime")
        if not s:
            continue
        try:
            start = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            continue
        wake = start - LOCK_LEAD - LEAD_IN
        # only games that have not locked yet, and only wakes we can still make
        if wake >= floor and wake < best:
            best = wake
    kind = "hour" if best == top_of_hour else "lock"
    return int(max(best, floor).timestamp()), kind


def main() -> None:
    date = (sys.argv[1] if len(sys.argv) > 1
            else dt.datetime.now(EASTERN).date().isoformat())
    ts, kind = next_wake(date)
    print(f"{ts} {kind}")


if __name__ == "__main__":
    main()
