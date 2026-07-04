"""
Board refresh: rebuild the day's board on every firing (as often as GitHub will
run the cron) so the picks always reflect the latest lineups, lines, and odds.

GitHub throttles scheduled crons hard (~2h between firings), which made the old
"only refresh a slot ~30 min before first pitch" logic miss its windows. So we
drop the slot bookkeeping entirely: every run just regenerates the whole board.
Games already underway stay frozen to their first-pitch snapshot (handled in
main._lock_started_games), so a refresh only moves games that haven't started.

Grading runs here too (finals move into the record). Telegram fires only when
the pick set actually changes, so frequent refreshes don't spam the phone.
"""

from __future__ import annotations

import json
import logging

from . import grade, main as picks_main, notify

log = logging.getLogger("pregame")

OUTPUT_DIR = picks_main.OUTPUT_DIR


def run() -> bool:
    date = picks_main.today_eastern()

    # remember the currently committed picks (+ coin-flip plays) to detect changes
    old_picks = None
    pf = OUTPUT_DIR / f"picks_{date}.json"
    if pf.exists():
        try:
            prev = json.loads(pf.read_text())
            old_picks = (prev.get("picks"), prev.get("coin_flips"))
        except ValueError:
            pass

    payload = picks_main.run(date)          # freezes started games, refreshes the rest
    picks_main.write_outputs(payload, date)
    grade.update_ledger(date)               # move any now-final games into the record

    if (payload.get("picks"), payload.get("coin_flips")) != old_picks:
        notify.send_telegram(picks_main.telegram_text(payload))
        log.info("picks changed -> board refreshed + telegram sent")
    else:
        log.info("board refreshed, picks unchanged -> no telegram")
    return True


def main() -> None:
    run()


if __name__ == "__main__":
    main()
