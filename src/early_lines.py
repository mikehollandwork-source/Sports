"""
Morning line snapshot - the record of the 'sharp window'.

ESPN exposes exactly two prices per game (open + current) with no timestamps, and
our board loop doesn't start until ~noon ET - so open->close movement can't be
split into the overnight/sharp window vs the afternoon/public pile-in. This
runner fires early (6am ET cron, before the noon loop) and freezes the slate's
prices at that moment into output/lines_early_<date>.json:

  espn:     [{away_abbr, home_abbr, *_open, *_current}]  (*_current = the 6am price)
  pinnacle: [{away_name, home_name, away_ml, home_ml}]   (sharp-book reference)

main.py then splits each pick's line move into early (open->6am) and late
(6am->now) shifts inside line_check, and signal_backtest grades which window's
move actually predicts winners once enough days accumulate. Recording only -
the live line signal (open->current) is unchanged.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import espn, pinnacle

log = logging.getLogger("early_lines")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")


def path_for(date: str) -> Path:
    return OUTPUT_DIR / f"lines_early_{date}.json"


def load(date: str) -> dict | None:
    """The day's morning snapshot, or None if the 6am run hasn't produced one."""
    try:
        return json.loads(path_for(date).read_text())
    except (OSError, ValueError):
        return None


def capture(date: str | None = None) -> dict:
    date = date or dt.datetime.now(EASTERN).date().isoformat()
    try:
        esp = espn.lines(date)
    except Exception as exc:
        log.warning("espn early snapshot failed: %s", exc)
        esp = []
    try:
        pin = pinnacle.lines()
    except Exception as exc:
        log.warning("pinnacle early snapshot failed: %s", exc)
        pin = []
    snap = {"date": date,
            "captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "espn": esp, "pinnacle": pin}
    OUTPUT_DIR.mkdir(exist_ok=True)
    path_for(date).write_text(json.dumps(snap, indent=2))
    log.info("early lines: %d espn / %d pinnacle row(s) -> %s",
             len(esp), len(pin), path_for(date).name)
    return snap


def main() -> None:
    capture()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
