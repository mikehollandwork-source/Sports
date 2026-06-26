"""
Telegram delivery for picks.

Sends a plain-text message via the Telegram Bot API using two repo secrets:
  TELEGRAM_BOT_TOKEN  - from @BotFather
  TELEGRAM_CHAT_ID    - your chat id (message the bot, then read it from
                        https://api.telegram.org/bot<token>/getUpdates)

No-ops quietly if either is unset, so the pipeline runs fine before you set them.
"""

from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger("notify")

LIMIT = 3900   # Telegram caps a message at 4096 chars; stay safely under


def _chunks(text: str, limit: int = LIMIT) -> list[str]:
    """Split into <=limit pieces on line boundaries (a single very long line is
    hard-split as a last resort) so a big board sends as several messages."""
    out, buf = [], ""
    for line in text.split("\n"):
        while len(line) > limit:                 # pathological single line
            out.append(line[:limit])
            line = line[limit:]
        if len(buf) + len(line) + 1 > limit:
            out.append(buf)
            buf = line
        else:
            buf = f"{buf}\n{line}" if buf else line
    if buf:
        out.append(buf)
    return out


def send_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        log.info("telegram not configured (set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID); skipping")
        return False
    parts = _chunks(text)
    ok = True
    for i, part in enumerate(parts, 1):
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat, "text": part, "disable_web_page_preview": True},
                timeout=20,
            )
            resp.raise_for_status()
        except Exception as exc:  # network/HTTP - degrade gracefully
            log.warning("telegram send failed (part %d/%d): %s", i, len(parts), exc)
            ok = False
    if ok:
        log.info("telegram message sent (%d part(s))", len(parts))
    return ok
