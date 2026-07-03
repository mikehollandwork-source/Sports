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
import re

import requests

from . import notify

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("listen")

API = "https://api.telegram.org/bot{}/{}"
GO_WORDS = {"go", "/go", "run", "/run"}


def _is_go(text: str) -> bool:
    """True when any word of the message is a go-word - so 'Go!', 'run it',
    'Go now' all trigger, not just a bare 'go'."""
    words = re.sub(r"[^a-z/ ]", " ", (text or "").lower()).split()
    return any(w in GO_WORDS for w in words)


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

    # self-diagnostics: which bot this token belongs to, and whether a webhook
    # is set (a webhook silently blocks getUpdates - the classic dead-'go' cause)
    try:
        me = requests.get(API.format(token, "getMe"), timeout=25).json().get("result", {})
        log.info("bot: @%s (%s)", me.get("username"), me.get("first_name"))
        wh = requests.get(API.format(token, "getWebhookInfo"), timeout=25).json().get("result", {})
        if wh.get("url"):
            log.warning("WEBHOOK IS SET (%s) - getUpdates gets nothing while a "
                        "webhook is active; delete it via deleteWebhook", wh["url"])
    except Exception as exc:
        log.warning("diagnostics failed: %s", exc)

    try:
        resp = requests.get(API.format(token, "getUpdates"), timeout=25)
        resp.raise_for_status()
        updates = resp.json().get("result", [])
    except Exception as exc:  # network/HTTP - degrade gracefully
        log.warning("getUpdates failed: %s", exc)
        _emit(False)
        return

    go = False
    unrecognized = None
    max_id = None
    for u in updates:
        max_id = u["update_id"]
        m = u.get("message") or u.get("edited_message") or {}
        cid = (m.get("chat") or {}).get("id")
        if str(cid) != str(chat):
            if cid is not None:   # someone texted the bot from a different chat
                log.warning("message from unexpected chat id %s (configured "
                            "TELEGRAM_CHAT_ID differs) - text: %r",
                            cid, (m.get("text") or "")[:40])
            continue
        text = (m.get("text") or "").strip()
        if _is_go(text):
            go = True
        elif text:
            unrecognized = text
    log.info("saw %d update(s); go=%s unrecognized=%r", len(updates), go, unrecognized)

    if max_id is not None:  # acknowledge everything we just read
        try:
            requests.get(API.format(token, "getUpdates"),
                         params={"offset": max_id + 1}, timeout=25)
        except Exception as exc:
            log.warning("ack (offset) failed: %s", exc)

    if go:
        notify.send_telegram("🟢 Got it — building today's board, hang tight…")
    elif unrecognized is not None:
        # never swallow a message silently: tell the user what would work
        notify.send_telegram(f"🤖 Saw “{unrecognized[:60]}” but didn't recognize it — "
                             "text “go” (or “run”) to build the board.")
    _emit(go)


if __name__ == "__main__":
    main()
