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
        stmt = (
            insert(Vacancy)
            .values(
                url=item["url"],
                title=item["title"],
                source=item.get("source"),
                listing_context=item.get("listing_context"),
                description_text=description_text or None
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
