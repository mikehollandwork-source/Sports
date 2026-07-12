"""
Telegram delivery for picks.

Sends a plain-text message via the Telegram Bot API using two repo secrets:
  TELEGRAM_BOT_TOKEN  - from @BotFather
  TELEGRAM_CHAT_ID    - one or more chat ids (comma- or space-separated) to send
                        to: a personal chat, a channel (-100...), and/or several
                        people. Each recipient must have messaged the bot first
                        (or added it as a channel admin). Get an id by messaging
                        the bot, then reading https://api.telegram.org/bot<token>/getUpdates

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


def _chat_ids(raw: str) -> list[str]:
    """Every recipient in TELEGRAM_CHAT_ID: a comma- or whitespace-separated list,
    so one secret can fan out to several people/channels. Keeps the personal IDs
    in the (private) secret instead of committing them to the repo."""
    return [c.strip() for c in raw.replace(",", " ").split() if c.strip()]


def send_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chats = _chat_ids(os.environ.get("TELEGRAM_CHAT_ID", ""))
    if not token or not chats:
        log.info("telegram not configured (set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID); skipping")
        return False
    parts = _chunks(text)
    ok = True
    for chat in chats:                       # fan out to every recipient
        for i, part in enumerate(parts, 1):
            try:
                resp = requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat, "text": part, "disable_web_page_preview": True},
                    timeout=20,
                )
                resp.raise_for_status()
            except Exception as exc:  # network/HTTP - degrade gracefully, keep going
                log.warning("telegram send failed (chat %s, part %d/%d): %s",
                            chat, i, len(parts), exc)
                ok = False
    if ok:
        log.info("telegram message sent to %d chat(s), %d part(s) each", len(chats), len(parts))
    return ok
