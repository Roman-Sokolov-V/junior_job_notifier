# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


from scrapy.exceptions import DropItem
from scrapy.exceptions import NotConfigured
from sqlalchemy.dialects.postgresql import insert

from db.crud import create_vacancy
from db.models import Vacancy

from sentence_transformers import SentenceTransformer

from db.session import create_engine_from_url, create_session_factory, get_db


# class PostgresPipeline:
#     """AI mode: повні поля вакансії для подальшого матчингу."""
#
#     def __init__(self, db_url: str | None):
#         self.db_url = db_url
#
#     @classmethod
#     def from_crawler(cls, crawler):
#         return cls(db_url=crawler.settings.get("DATABASE_URL"))
#
#     def open_spider(self, spider):
#         if not self.db_url:
#             raise NotConfigured("DATABASE_URL is not set.")
#         self.engine = create_engine_from_url(self.db_url)
#         self.Session = create_session_factory(self.engine)
#
#     def process_item(self, item, spider):
#         description_text = item.get("description_text", "") or ""
#         stmt = (
#             insert(Vacancy)
#             .values(
#                 url=item["url"],
#                 title=item["title"],
#                 source=item.get("source"),
#                 listing_context=item.get("listing_context"),
#                 description_text=description_text or None
#             )
#             .on_conflict_do_nothing(constraint="uq_vacancies_url_title")
#         )
#         with self.Session() as session:
#             with session.begin():
#                 result = session.execute(stmt)
#
#         if result.rowcount == 1:
#             item["is_new"] = True
#             return item
#         raise DropItem(f"URL+Title already exists in db: {item}")
#
#     def close_spider(self, spider):
#         if hasattr(self, "engine") and self.engine:
#             self.engine.dispose()

class PgvectorPipeline:
    """ Збереження результатів в бд з ембендінгом"""

    def __init__(self, ai_model_name: str | None, model: SentenceTransformer) -> None:
        self.ai_model_name = ai_model_name
        self.model = model

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            ai_model_name=crawler.settings.get("AI_MODEL_NAME"),
            model=crawler.settings.get("AI_MODEL_INSTANCE"),
        )

    def open_spider(self, spider):
        if not self.ai_model_name:
            raise NotConfigured("AI_MODEL_NAME is not set.")
        #self.model = SentenceTransformer(self.ai_model_name)

    def process_item(self, item, spider):
        description_text = item.get("description_text", "") or ""
        embedding = self.model.encode(description_text).tolist() if description_text else None
        embedding_model = self.ai_model_name if embedding is not None else None
        vacancy_data = {
            "url": item["url"],
            "title": item["title"],
            "source": item.get("source"),
            "listing_context": item.get("listing_context"),
            "description_text": description_text or None,
            "embedding": embedding,
            "embedding_model": embedding_model,
        }
        with get_db() as db:
            is_new = create_vacancy(db, vacancy_data)
        if is_new:
            item["embedding"] = embedding
            item["embedding_model"] = self.ai_model_name
            return item
        raise DropItem(f"URL+Description already exists in db: {item}")

