import asyncio
from html import escape
import logging
import os

from httpx import AsyncClient
import dotenv
from sqlalchemy import Row, Sequence, RowMapping

from db.session import get_db
from db.crud import get_not_notified, bulk_mark_notified, get_telegram_id
from filter.schemas import MatchData

logger = logging.getLogger(__name__)

dotenv.load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")


semaphore = asyncio.Semaphore(10)


async def send_one_notification(client: AsyncClient, data: Row) -> int | None:
    if not data.telegram_user_id or not data.url:
        return None
    title = escape(data.title or "")
    url = escape(data.url or "")
    source = escape(data.source or "")
    reason = escape(data.reason or "None")

    message = (
        f"🌟 <b>Нова вакансія!</b>\n\n"
        f"📋 <b>Назва:</b> {title}\n"
        f'🔗 <a href="{url}">Переглянути</a>\n'
        f"🧾 <b>З ресурсу:</b> {source}\n"
        f"<b>LLM reason</b> {reason}\n"
        f"<b>LLM confidence </b>{data.confidence}\n"
        f"<b>semantic score</b>{data.semantic_score}\n"
    )

    payload = {
        "chat_id": data.telegram_user_id,
        "text": message,
        "parse_mode": "HTML",
    }

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    async with semaphore:
        try:
            response = await client.post(api_url, data=payload, timeout=10)
            response.raise_for_status()
            return data.match_id
        except Exception as e:
            logging.error("Telegram error: %s", e)
            return None


async def start_notification() -> None:
    logging.info("_______________start notification")
    with get_db() as db:
        notification_data = get_not_notified(db)
        logging.debug("знайдено %s", len(notification_data))
    num_need_to_notify = len(notification_data)
    if num_need_to_notify == 0:
        logging.info("Нема матчів, зі статусом - не повідомлені")
        return None
    async with AsyncClient() as client:
        coroutines = [send_one_notification(client, data) for data in notification_data]
        gathered = await asyncio.gather(*coroutines)
    notified = [item for item in gathered if item is not None]

    if (num_notified := len(notified)) > 0:
        with get_db() as db:
            bulk_mark_notified(db, notified)
        logging.info("Успішно повідомлено %s з %s", num_notified, num_need_to_notify)
    else:
        logging.warning("Жодного успішного повідомлення")

async def not_found_notification(
        user_id: int, data: list[MatchData] | None = None,
        vacancies: Sequence[RowMapping] | None = None
) -> None:
    logging.info("______________not_found notification")
    with get_db() as db:
        telegram_user_id = get_telegram_id(db, user_id)
    if telegram_user_id:
        if data:
            top_not_matched = "\n\n<b>".join(
                [
                    f"\n vac: {item.vacancy_id},"
                    f"\n semantic: {item.semantic_score},"
                    f"\n confidence: {item.confidence}"
                    f"\n reason: {item.reason}"
                    for
                    item
                    in data
                ]
            )
        elif vacancies:
            sorted_vacancies = sorted(
                vacancies,
                key=lambda vac: vac.similarity_expr,
                reverse=True
            )[:5]
            top_not_matched = "\n\n<b>".join(
                [
                    f"\n vac: {item.vacancy_id},"
                    f"\n semantic: {item.similarity_expr},"
                    f"\n title: {item.title}"
                    f"\n url: {item.url}"
                    f"\n description: {item.description_text[:50]}..."
                    for
                    item
                    in sorted_vacancies
                ]
            )
        message = (
            f"🌟 <b>На жаль сьогодні не знайдено жодної підходящої вакансії</b>\n\n"
            f"📋 <b>Про всяк випадок ось рапорт про топ 5 найкращих:\n"
            f"{top_not_matched}"
        )
        payload = {
            "chat_id": telegram_user_id,
            "text": message,
            "parse_mode": "HTML",
        }

        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        async with AsyncClient() as client:
            try:
                response = await client.post(api_url, data=payload, timeout=10)
                response.raise_for_status()
            except Exception as e:
                logging.error("Telegram error: %s", e)
                return None
