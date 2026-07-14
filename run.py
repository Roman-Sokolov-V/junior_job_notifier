import logging

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from sentence_transformers import SentenceTransformer

from common_settings import setup_logging, current_model_name
from db.crud import get_vacancies_urls
from db.session import get_db
from filter.matching import filter_vacancies
from scrap_vac.spiders.conversion_rate import ConversionRateSpider
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
    settings["AI_MODEL_INSTANCE"] = model
    with get_db() as db:
        settings["EXISTING_URLS"] = set(get_vacancies_urls(db))

    process = CrawlerProcess(settings)

    process.crawl(BreezySpider)
    process.crawl(GenTechSpider)
    process.crawl(TietoSpider)
    process.crawl(ThingsboardSpider)
    process.crawl(StarGlobalSpider)
    process.crawl(NewxelSpider)
    process.crawl(ConversionRateSpider)
    process.crawl(SigmaTechnologySpider)
    process.start()


if __name__ == '__main__':
    setup_logging()
    logger = logging.getLogger(__name__)
    model = create_ai_model(current_model_name)
    #main(model)
    filter_vacancies(model)
    #start_notification()
#todo реалізувати видалення застарілих вакансій