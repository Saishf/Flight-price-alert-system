from __future__ import annotations

import os
from urllib.parse import quote

import requests


def send_telegram(message: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Telegram notification skipped: bot token or chat id not configured.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(url, data=payload, timeout=20)
        response.raise_for_status()
        return True
    except Exception as exc:  # pragma: no cover - best effort integration
        print(f"Telegram send failed: {exc}")
        return False
