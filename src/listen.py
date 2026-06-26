"""
Poll Telegram for a "go" command and tell the workflow whether to run the board.

Stateless: getUpdates returns updates that haven't been acknowledged yet; after
scanning we acknowledge them all (offset = max update_id + 1) so the next poll
only sees new messages. Only messages from the configured TELEGRAM_CHAT_ID count,
so nobody else can trigger a run. Writes `should_run=true|false` to GITHUB_OUTPUT.
No-ops (should_run=false) when Telegram isn't configured.
"""

from __future__ import annotations

import logging
import os

import requests

from . import notify

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("listen")

API = "https://api.telegram.org/bot{}/{}"
GO_WORDS = {"go", "/go", "run", "/run"}


def _emit(should_run: bool) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"should_run={'true' if should_run else 'false'}\n")
    log.info("should_run=%s", should_run)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        log.info("telegram not configured; nothing to poll")
        _emit(False)
        return

    try:
        resp = requests.get(API.format(token, "getUpdates"), timeout=25)
        resp.raise_for_status()
        updates = resp.json().get("result", [])
    except Exception as exc:  # network/HTTP - degrade gracefully
        log.warning("getUpdates failed: %s", exc)
        _emit(False)
        return

    go = False
    max_id = None
    for u in updates:
        max_id = u["update_id"]
        m = u.get("message") or u.get("edited_message") or {}
        if str((m.get("chat") or {}).get("id")) != str(chat):
            continue
        if (m.get("text") or "").strip().lower() in GO_WORDS:
            go = True

    if max_id is not None:  # acknowledge everything we just read
        try:
            requests.get(API.format(token, "getUpdates"),
                         params={"offset": max_id + 1}, timeout=25)
        except Exception as exc:
            log.warning("ack (offset) failed: %s", exc)

    if go:
        notify.send_telegram("🟢 Got it — building today's board, hang tight…")
    _emit(go)


if __name__ == "__main__":
    main()
