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
    """ Збереження результатів в бд з ембендінгом"""

    def __init__(self, ai_model_name: str | None, model: SentenceTransformer) -> None:
        self.ai_model_name = ai_model_name
        self.model = model

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            ai_model_name=crawler.settings.get("AI_MODEL_NAME"),
            model=crawler.settings.get(
                "AI_MODEL_INSTANCE"
            ),
        )

    def open_spider(self, spider=None):
        if not self.ai_model_name:
            raise NotConfigured("AI_MODEL_NAME is not set.")
        if not self.model:
            raise NotConfigured("model is not set.")


    def process_item(self, item):

        embedding_text = item.get("embedding_text", None)
        embedding = self.model.encode(embedding_text).tolist() if embedding_text else None
        embedding_model = self.ai_model_name if embedding is not None else None
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
            "embedding_text": embedding_text,
        }
        with get_db() as db:
            is_new = create_vacancy(db, vacancy_data)
        if is_new:
            item["embedding"] = embedding
            item["embedding_model"] = self.ai_model_name
            return item
        raise DropItem(f"URL+Description already exists in db: {item}")

