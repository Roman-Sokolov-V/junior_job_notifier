import os

# Обмежуємо внутрішню паралелізацію CPU-бібліотек (OpenMP/MKL/tokenizers),
# які використовує sentence-transformers. Без цього на завершенні процесу
# лишались "leaked semaphore" від пулу воркерів і скрипт міг зависати
# перед виходом. На CI (2 ядра) паралелізація й так майже не дає виграшу.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["MKL_NUM_THREADS"] = "1"

import logging

from datetime import datetime, timedelta

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from sentence_transformers import SentenceTransformer

from common_settings import setup_logging, current_model_name
from db.crud import get_vacancies_urls, mark_urls_as_seen, delete_vacancies_not_seen_since, get_last_run, create_state
from db.session import get_db
from filter.matching import filter_vacancies
from scrap_vac.spiders.conversion_rate import ConversionRateSpider
from scrap_vac.spiders.epam import EpamSpider
from scrap_vac.spiders.newxel import NewxelSpider
from scrap_vac.spiders.sigma_technology import SigmaTechnologySpider
from scrap_vac.spiders.star_global import StarGlobalSpider
from scrap_vac.spiders.thingsboard import ThingsboardSpider
from scrap_vac.spiders.breezy import BreezySpider
from scrap_vac.spiders.gen_tech import GenTechSpider
from scrap_vac.spiders.tieto import TietoSpider

from dotenv import load_dotenv

from telegram.notification import start_notification

load_dotenv()


def create_ai_model(model_name: str) -> SentenceTransformer:
    model = SentenceTransformer(model_name)
    return model

def main(model: SentenceTransformer):
    settings = get_project_settings()
    with get_db() as db:
        existing_urls = set(get_vacancies_urls(db))

    settings["EXISTING_URLS"] = existing_urls
    settings["SEEN_EXISTING_URLS"] = set()
    settings["AI_MODEL_INSTANCE"] = model

    process = CrawlerProcess(settings)

    process.crawl(BreezySpider)
    process.crawl(GenTechSpider)
    process.crawl(TietoSpider)
    process.crawl(ThingsboardSpider)
    process.crawl(StarGlobalSpider)
    process.crawl(NewxelSpider)
    process.crawl(ConversionRateSpider)
    process.crawl(SigmaTechnologySpider)
    process.crawl(EpamSpider)
    process.start()

    seen_existing_urls = settings["SEEN_EXISTING_URLS"]

    with get_db() as db:
        # оновлюємо last_seen_at для тих, що реально зустрілись
        mark_urls_as_seen(db, seen_existing_urls)

        now = datetime.now()
        stale_cutoff = now - timedelta(days=7)
        state = get_last_run(db)
        if state is None:
            create_state(db)
        else:
            if state.updated_at > now - timedelta(days=3):
                # видаляємо тільки ті, що не бачились довше певного порогу враховуючи можливі перерви в запуску
                delete_vacancies_not_seen_since(db, stale_cutoff)
            state.updated_at = now

if __name__ == '__main__':
    setup_logging()
    logger = logging.getLogger(__name__)
    try:
        model = create_ai_model(current_model_name)
        main(model)
        filter_vacancies(model)
        start_notification()
    finally:
        import gc
        del model
        gc.collect()
