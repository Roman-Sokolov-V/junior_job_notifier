# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


import hashlib

import psycopg2
from scrapy.exceptions import DropItem
import requests
from scrapy.exceptions import NotConfigured


class PostgresPipeline:
    """Classic mode: збереження лише url + title (оригінальна схема)."""

    def __init__(self, db_url):
        self.db_url = db_url

    @classmethod
    def from_crawler(cls, crawler):
        return cls(db_url=crawler.settings.get("DATABASE_URL"))

    def open_spider(self, spider):
        self.conn = psycopg2.connect(self.db_url)
        self.cur = self.conn.cursor()
        self.cur.execute("""
                         CREATE TABLE IF NOT EXISTS vacancies (
                             id SERIAL PRIMARY KEY,
                             url TEXT NOT NULL,
                             title TEXT NOT NULL,
                             added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                             UNIQUE(url, title)
                         )
                         """)
        self.conn.commit()

    def process_item(self, item, spider):
        self.cur.execute(
            """
            INSERT INTO vacancies (url, title)
            VALUES (%s, %s) ON CONFLICT (url, title) DO NOTHING
            """,
            (item["url"], item["title"]),
        )
        self.conn.commit()

        if self.cur.rowcount == 1:
            item["is_new"] = True
            return item
        raise DropItem(f"URL+Title already exists in db: {item}")

    def close_spider(self, spider):
        if hasattr(self, "cur") and self.cur:
            try:
                self.cur.close()
            except Exception:
                pass
        if hasattr(self, "conn") and self.conn:
            try:
                self.conn.close()
            except Exception:
                pass


class PostgresPipelineAI:
    """AI mode: url, title + поля для матчингу (source, listing_context, description_text, content_hash)."""

    def __init__(self, db_url):
        self.db_url = db_url

    @classmethod
    def from_crawler(cls, crawler):
        return cls(db_url=crawler.settings.get("DATABASE_URL"))

    def open_spider(self, spider):
        self.conn = psycopg2.connect(self.db_url)
        self.cur = self.conn.cursor()
        # Базова таблиця — як у класичному режимі; додаткові колонки лише для AI.
        self.cur.execute("""
                         CREATE TABLE IF NOT EXISTS vacancies (
                             id SERIAL PRIMARY KEY,
                             url TEXT NOT NULL,
                             title TEXT NOT NULL,
                             added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                             UNIQUE(url, title)
                         )
                         """)
        self.cur.execute("ALTER TABLE vacancies ADD COLUMN IF NOT EXISTS source TEXT")
        self.cur.execute("ALTER TABLE vacancies ADD COLUMN IF NOT EXISTS listing_context TEXT")
        self.cur.execute("ALTER TABLE vacancies ADD COLUMN IF NOT EXISTS description_text TEXT")
        self.cur.execute("ALTER TABLE vacancies ADD COLUMN IF NOT EXISTS content_hash TEXT")
        self.conn.commit()

    def process_item(self, item, spider):
        description_text = item.get("description_text", "") or ""
        content_hash = (
            hashlib.md5(description_text.encode("utf-8")).hexdigest()
            if description_text
            else None
        )

        self.cur.execute(
            """
            INSERT INTO vacancies (url, title, source, listing_context, description_text, content_hash)
            VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (url, title) DO NOTHING
            """,
            (
                item["url"],
                item["title"],
                item.get("source"),
                item.get("listing_context"),
                description_text or None,
                content_hash,
            ),
        )
        self.conn.commit()

        if self.cur.rowcount == 1:
            item["is_new"] = True
            return item
        raise DropItem(f"URL+Title already exists in db: {item}")

    def close_spider(self, spider):
        if hasattr(self, "cur") and self.cur:
            try:
                self.cur.close()
            except Exception:
                pass
        if hasattr(self, "conn") and self.conn:
            try:
                self.conn.close()
            except Exception:
                pass


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
