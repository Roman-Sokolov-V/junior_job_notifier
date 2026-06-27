# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


import hashlib

import requests
from scrapy.exceptions import DropItem
from scrapy.exceptions import NotConfigured
from sqlalchemy.dialects.postgresql import insert
from scrap_vac.db.models import Vacancy
from scrap_vac.db.session import create_engine_from_url, create_session_factory


class PostgresPipeline:
    """Classic mode: зберігає лише url + title (ORM + upsert)."""

    def __init__(self, db_url: str | None):
        self.db_url = db_url

    @classmethod
    def from_crawler(cls, crawler):
        return cls(db_url=crawler.settings.get("DATABASE_URL"))

    def open_spider(self, spider):
        if not self.db_url:
            raise NotConfigured("DATABASE_URL is not set.")
        self.engine = create_engine_from_url(self.db_url)
        self.Session = create_session_factory(self.engine)

    def process_item(self, item, spider):
        stmt = (
            insert(Vacancy)
            .values(url=item["url"], title=item["title"])
            .on_conflict_do_nothing(constraint="uq_vacancies_url_title")
        )
        with self.Session() as session:
            with session.begin():
                result = session.execute(stmt)

        if result.rowcount == 1:
            item["is_new"] = True
            return item
        raise DropItem(f"URL+Title already exists in db: {item}")

    def close_spider(self, spider):
        if hasattr(self, "engine") and self.engine:
            self.engine.dispose()


class PostgresPipelineAI:
    """AI mode: повні поля вакансії для подальшого матчингу."""

    def __init__(self, db_url: str | None):
        self.db_url = db_url

    @classmethod
    def from_crawler(cls, crawler):
        return cls(db_url=crawler.settings.get("DATABASE_URL"))

    def open_spider(self, spider):
        if not self.db_url:
            raise NotConfigured("DATABASE_URL is not set.")
        self.engine = create_engine_from_url(self.db_url)
        self.Session = create_session_factory(self.engine)

    def process_item(self, item, spider):
        description_text = item.get("description_text", "") or ""
        content_hash = (
            hashlib.md5(description_text.encode("utf-8")).hexdigest()
            if description_text
            else None
        )

        stmt = (
            insert(Vacancy)
            .values(
                url=item["url"],
                title=item["title"],
                source=item.get("source"),
                listing_context=item.get("listing_context"),
                description_text=description_text or None,
                content_hash=content_hash,
            )
            .on_conflict_do_nothing(constraint="uq_vacancies_url_title")
        )
        with self.Session() as session:
            with session.begin():
                result = session.execute(stmt)

        if result.rowcount == 1:
            item["is_new"] = True
            return item
        raise DropItem(f"URL+Title already exists in db: {item}")

    def close_spider(self, spider):
        if hasattr(self, "engine") and self.engine:
            self.engine.dispose()



class TelegramPipeline:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    @classmethod
    def from_crawler(cls, crawler):
        token = crawler.settings.get("TELEGRAM_BOT_TOKEN")
        chat_id = crawler.settings.get("TELEGRAM_CHAT_ID")

        if not token or not chat_id:
            raise NotConfigured("Telegram Token or Chat ID not found!")

        return cls(token, chat_id)

    def process_item(self, item, spider):
        message = (
            f"🌟 *Нова вакансія!*\n\n"
            f"📋 *Назва:* {item['title']}\n"
            f"🔗 [Переглянути]({item['url']})"
        )

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }

        try:
            response = requests.post(self.api_url, data=payload)
            response.raise_for_status()
        except Exception as e:
            spider.logger.error(f"Telegram error: {e}")

        return item
