"""
Off-hours line snapshots - the record of the sharp windows.

ESPN exposes exactly two prices per game (open + current) with no timestamps, and
our board loop doesn't start until ~noon ET - so open->close movement can't be
split by WHEN it happened. Two small crons freeze the slate's prices off-hours:

  evening (~11pm ET, for TOMORROW's slate) -> lines_evening_<date>.json
      the fresh openers a few hours after they post: open->11pm isolates the
      "instant strike" sharps put on a new low-limit test line
  morning (~6am ET, for today's slate)     -> lines_early_<date>.json
      the 6am price: open->6am = the full overnight/sharp window,
      6am->close = the daytime/public window

Each file: {date, captured_utc,
            espn:     [{away_abbr, home_abbr, *_open, *_current}],   (*_current = price at capture)
            pinnacle: [{away_name, home_name, away_ml, home_ml}]}    (sharp-book reference)

main.py threads the checkpoints into each pick's line_check (strike_shift /
overnight_shift / early_shift / late_shift / timing) and signal_backtest grades
which window's move actually predicts winners once days accumulate. Recording
only - the live line signal (open->current) is unchanged.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import espn, pinnacle

log = logging.getLogger("early_lines")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")


def path_for(date: str, reading: str = "early") -> Path:
    return OUTPUT_DIR / f"lines_{reading}_{date}.json"


def load(date: str, reading: str = "early") -> dict | None:
    """A day's snapshot ('early' = 6am, 'evening' = 11pm the night before), or
    None if that cron hasn't produced one."""
    try:
        return json.loads(path_for(date, reading).read_text())
    except (OSError, ValueError):
        return None


def capture(date: str | None = None, reading: str = "early") -> dict:
    if date is None:
        today = dt.datetime.now(EASTERN).date()
        # the evening run happens the NIGHT BEFORE the slate it snapshots
        date = (today + dt.timedelta(days=1)).isoformat() if reading == "evening" \
            else today.isoformat()
    try:
        esp = espn.lines(date)
    except Exception as exc:
        log.warning("espn %s snapshot failed: %s", reading, exc)
        esp = []
    try:
        pin = pinnacle.lines()
    except Exception as exc:
        log.warning("pinnacle %s snapshot failed: %s", reading, exc)
        pin = []
    snap = {"date": date, "reading": reading,
            "captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "espn": esp, "pinnacle": pin}
    OUTPUT_DIR.mkdir(exist_ok=True)
    path_for(date, reading).write_text(json.dumps(snap, indent=2))
    log.info("%s lines: %d espn / %d pinnacle row(s) -> %s",
             reading, len(esp), len(pin), path_for(date, reading).name)
    return snap


def history_path(date: str) -> Path:
    return OUTPUT_DIR / f"lines_history_{date}.json"


def load_history(date: str) -> list:
    """The day's dense, append-only line checkpoints (many per day), or []."""
    try:
        return json.loads(history_path(date).read_text())
    except (OSError, ValueError):
        return []


def append_checkpoint(date: str | None = None) -> None:
    """Append one timestamped price checkpoint for EVERY game to the day's line
    history. Called on every board-loop tick, so every game is captured many
    times a day off the loop's reliable ~hourly schedule - not the two fragile
    off-hours crons. Append-only (a missed tick can't wipe the day); fail-soft."""
    if date is None:
        date = dt.datetime.now(EASTERN).date().isoformat()
    try:
        esp = espn.lines(date)
    except Exception as exc:
        log.warning("line checkpoint espn fetch failed: %s", exc)
        return
    if not esp:
        return
    hist = load_history(date)
    hist.append({"captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 "espn": esp})
    OUTPUT_DIR.mkdir(exist_ok=True)
    history_path(date).write_text(json.dumps(hist, indent=1))
    log.info("line checkpoint: %d games -> %s (%d today)", len(esp), history_path(date).name, len(hist))


def main() -> None:
    ap = argparse.ArgumentParser(description="Freeze the slate's current prices to a snapshot file")
    ap.add_argument("--evening", action="store_true",
                    help="the ~11pm ET reading of TOMORROW's fresh openers (default: 6am for today)")
    capture(reading="evening" if ap.parse_args().evening else "early")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
