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


def send_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        log.info("telegram not configured (set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID); skipping")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
            timeout=20,
        )
        resp.raise_for_status()
        log.info("telegram message sent")
        return True
    except Exception as exc:  # network/HTTP - degrade gracefully
        log.warning("telegram send failed: %s", exc)
        return False
