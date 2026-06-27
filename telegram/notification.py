from html import escape
import logging
import os
import requests
import dotenv

from scrap_vac.db.session import get_db
from scrap_vac.db.crud import get_not_notified

dotenv.load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")


def start_notification():
    with get_db() as db:
        notification_data = get_not_notified(db)

    for data in notification_data:

        if not data.telegram_user_id or not data.url:
            continue

        title = escape(data.title or "")
        url = escape(data.url or "")
        source = escape(data.source or "")

        message = (
            f"🌟 <b>Нова вакансія!</b>\n\n"
            f"📋 <b>Назва:</b> {title}\n"
            f"🔗 <a href=\"{url}\">Переглянути</a>\n"
            f"🧾 <b>З ресурсу:</b> {source}"
        )

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }

        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        try:
            response = requests.post(api_url, data=payload, timeout=10)

            if not response.ok:
                print(response.text)

            response.raise_for_status()

        except Exception as e:
            logging.error(f"Telegram error: {e}")