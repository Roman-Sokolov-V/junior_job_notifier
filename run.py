from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from match_new_batch import filter_vacancies
from scrap_vac.db.crud import get_vacancies_urls
from scrap_vac.db.session import get_db
from scrap_vac.spiders.breezy import BreezySpider
from scrap_vac.spiders.gen_tech import GenTechSpider
from scrap_vac.spiders.star_global_ai import StarGlobalAiSpider
from scrap_vac.spiders.thingsboard_ai import ThingsboardAiSpider
from scrap_vac.spiders.tieto import TietoSpider
from scrap_vac.spiders.breezy_ai import BreezyAISpider
from scrap_vac.spiders.gen_tech_ai import GenTechAISpider
from scrap_vac.spiders.tieto_ai import TietoAISpider
from telegram.notification import start_notification


from dotenv import load_dotenv
load_dotenv()



def main():
    settings = get_project_settings()
    with get_db() as db:
        settings["EXISTING_URLS"] = set(get_vacancies_urls(db))

    process = CrawlerProcess(settings)
    if not settings.getbool("AI_MODE"):
        process.crawl(BreezySpider)
        process.crawl(GenTechSpider)
        process.crawl(TietoSpider)
    else:
        process.crawl(BreezyAISpider)
        process.crawl(GenTechAISpider)
        process.crawl(TietoAISpider)
        process.crawl(ThingsboardAiSpider)
        process.crawl(StarGlobalAiSpider)
    process.start()


if __name__ == '__main__':
    main()
    filter_vacancies()
    start_notification()
