"""
Board refresh: rebuild the day's board on every firing (as often as GitHub will
run the cron) so the picks always reflect the latest lineups, lines, and odds.

GitHub throttles scheduled crons hard (~2h between firings), which made the old
"only refresh a slot ~30 min before first pitch" logic miss its windows. So we
drop the slot bookkeeping entirely: every run just regenerates the whole board.
Games already underway stay frozen to their first-pitch snapshot (handled in
main._lock_started_games), so a refresh only moves games that haven't started.

Grading runs here too (finals move into the record). Telegram fires when the
pick set changes, OR on every run started with --telegram (the hourly
on-the-hour board post the workflow sends once per clock hour).
"""

from __future__ import annotations

import json
import logging

from . import early_lines, gate_report, grade, main as picks_main, notify, pick_watch

log = logging.getLogger("pregame")

OUTPUT_DIR = picks_main.OUTPUT_DIR


def _board_state(payload: dict) -> tuple:
    """What the board SHOWS, which is what a change must be measured against.

    This compared picks and coin-flips only. The board posts PROPS too, and
    props are the half that changes at a lock wake - the moment both lineups
    post, the selection freezes and two hitters appear. A lock wake runs
    without --telegram, so `force_telegram` is False, and with no moneyline
    play on the slate `picks` is empty and unchanged all day. Both halves of
    the test were therefore False at exactly the moment the board gained its
    content, and nothing was sent.

    Seen on 2026-10-14: a no-play slate whose two props (Contreras, Turang)
    appeared at the lock and were announced by nothing.

    Only the PUBLISHED props count - `props_locked` is the publication gate,
    so a provisional selection churning in the background must not put a
    board on the phone it is not yet willing to show.
    """
    props = []
    for g in payload.get("games") or []:
        pc = g.get("pick_criteria") or {}
        if pc.get("props_locked"):
            props.append((g.get("game_pk"),
                          tuple(sorted((b.get("player"), b.get("odds"))
                                       for b in pc.get("props") or [])),
                          ((pc.get("hr_prop") or {}).get("player"),
                           (pc.get("hr_prop") or {}).get("odds"))))
    return (payload.get("picks"), payload.get("coin_flips"), tuple(props))


def run(force_telegram: bool = False) -> bool:
    date = picks_main.today_eastern()

    # remember what the BOARD currently shows, to detect changes
    old_picks = None
    pf = OUTPUT_DIR / f"picks_{date}.json"
    if pf.exists():
        try:
            prev = json.loads(pf.read_text())
            old_picks = _board_state(prev)
        except ValueError:
            pass

    payload = picks_main.run(date)          # freezes started games, refreshes the rest
    picks_main.write_outputs(payload, date)
    early_lines.append_checkpoint(date)     # dense line history: every game, every tick
    grade.update_ledger(date)               # move any now-final games into the record

    # once the LAST game of a slate is final, send a one-time end-of-day recap.
    # check today and the prior day (late games finish after midnight ET, so the
    # slate that just wrapped may be dated yesterday by the time it's all final).
    import datetime as _dt
    from . import prop_grade
    prev = (_dt.date.fromisoformat(date) - _dt.timedelta(days=1)).isoformat()
    for d in (date, prev):
        prop_grade.update(d)                # settle the day's hit props (own ledger)
        grade.send_day_recap_if_complete(d, notify.send_telegram)

    changed = _board_state(payload) != old_picks
    if force_telegram or changed:
        notify.send_telegram(picks_main.telegram_text(payload))
        log.info("telegram sent (%s)", "hourly on-the-hour" if force_telegram and not changed
                 else "picks changed")
    else:
        log.info("board refreshed, picks unchanged -> no telegram")

    # Withdrawal alerts belong HERE, not in main.main(): the hourly refresh is
    # the only path that re-evaluates a slate repeatedly, so it is the only path
    # where a pick can be withdrawn. main.main() runs once a day and would never
    # have seen one. Runs unconditionally - a withdrawal is exactly the case
    # where `changed` is True but the board post above may say nothing useful,
    # and it is also the case a dropped cron makes invisible.
    try:
        pick_watch.check(payload.get("games") or [], date)
    except Exception as exc:
        log.warning("pick watch failed (board unaffected): %s", exc)

    # Gate breakdown for the slate. The board reports only the FIRST gate a game
    # failed, so a near-miss and a game that failed everything read identically.
    # Written to output/, which the workflow already commits wholesale.
    try:
        (OUTPUT_DIR / f"gates_{date}.md").write_text(gate_report.build(date))
    except Exception as exc:
        log.warning("gate report failed (board unaffected): %s", exc)
    return True


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Refresh the board (and optionally post it)")
    ap.add_argument("--telegram", action="store_true",
                    help="always post the board to Telegram this run (the hourly on-the-hour send)")
    run(force_telegram=ap.parse_args().telegram)


if __name__ == "__main__":
    main()
