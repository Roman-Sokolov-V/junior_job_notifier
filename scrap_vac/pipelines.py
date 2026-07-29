# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


from scrapy.exceptions import DropItem
from scrapy.exceptions import NotConfigured

from sentence_transformers import SentenceTransformer

from db.crud import create_vacancy
from db.session import get_db


class PgvectorPipeline:
    """Збереження результатів в бд з ембедінгом"""

    def __init__(self, ai_model_name: str | None, model: SentenceTransformer) -> None:
        self.ai_model_name = ai_model_name
        self.model = model

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            ai_model_name=crawler.settings.get("AI_MODEL_NAME"),
            model=crawler.settings.get("AI_MODEL_INSTANCE"),
        )

    def open_spider(self, spider=None):
        if not self.ai_model_name:
            raise NotConfigured("AI_MODEL_NAME is not set.")
        if not self.model:
            raise NotConfigured("model is not set.")

    def process_item(self, item):
        text = item.get("description_text", None)
        if not text:
            raise DropItem("No description provided.")
        embedding = self.model.encode(text).tolist()
        embedding_model = self.ai_model_name
        vacancy_data = {
            "url": item["url"],
            "title": item["title"],
            "source": item.get("source"),
            "listing_context": item.get("listing_context"),
            "description_text": item.get("description_text"),
            "embedding": embedding,
            "embedding_model": embedding_model,
            "requirements": item.get("requirements"),
            "nice_to_have": item.get("nice_to_have"),
            "experience": item.get("experience"),
            "seniority": item.get("seniority"),
        }
        with get_db() as db:
            create_vacancy(db, vacancy_data)
