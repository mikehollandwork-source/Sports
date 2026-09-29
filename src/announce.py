"""
One-off channel announcement: send arbitrary text to the Telegram channel
through the same notify pipeline the board uses.

Manual-only (announce.yml workflow_dispatch). It never writes picks files and
never touches the ledger, so nothing sent here is ever graded or counted in the
record - it's for specials, welcome notes, and service announcements.
"""

from __future__ import annotations

import logging
import os
import sys

from . import notify


def main() -> None:
    text = os.environ.get("ANNOUNCE_TEXT", "").strip() or " ".join(sys.argv[1:]).strip()
    if not text:
        raise SystemExit("nothing to send: set ANNOUNCE_TEXT or pass the text as arguments")
    if not notify.send_telegram(text):
        raise SystemExit("telegram send failed")
    print("announcement sent")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
