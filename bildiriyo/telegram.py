from __future__ import annotations

import html
import logging
import os
import time

import requests

log = logging.getLogger(__name__)
LIMIT = 4000  # Telegram mesaj sınırı 4096


class Telegram:
    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        self.dry_run = not (self.token and self.chat_id)
        if self.dry_run:
            log.warning("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID yok: mesajlar sadece ekrana yazılacak")

    def send(self, text: str) -> bool:
        if self.dry_run:
            print("\n" + text + "\n" + "-" * 40)
            return True
        for attempt in range(5):
            try:
                r = requests.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML",
                          "disable_web_page_preview": True},
                    timeout=30,
                )
            except requests.RequestException as e:
                log.warning("Telegram hatası: %s", e)
                time.sleep(5)
                continue
            if r.status_code == 429:
                time.sleep(r.json().get("parameters", {}).get("retry_after", 10) + 1)
                continue
            if r.ok:
                time.sleep(1.1)  # grup sınırı: ~20 mesaj/dk
                return True
            log.error("Telegram %s: %s", r.status_code, r.text[:300])
            return False
        return False

    def send_long(self, header: str, lines: list[str]) -> bool:
        """Satırları 4096 sınırını aşmayacak şekilde birden çok mesaja böler."""
        ok, buf = True, header
        for line in lines:
            if len(buf) + len(line) + 1 > LIMIT:
                ok &= self.send(buf)
                buf = header + " (devam)"
            buf += "\n" + line
        return self.send(buf) and ok


def esc(s: str) -> str:
    return html.escape(s or "", quote=False)
