from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from scrap_vac.spiders.breezy import BreezySpider
from scrap_vac.spiders.gen_tech import GenTechSpider
from scrap_vac.spiders.tieto import TietoSpider
from scrap_vac.spiders.breezy_ai import BreezyAISpider
from scrap_vac.spiders.gen_tech_ai import GenTechAISpider
from scrap_vac.spiders.tieto_ai import TietoAISpider


from dotenv import load_dotenv
load_dotenv()



 # todo
 # 1 запуск спайдерів, оновлення бд
 # 2 
 #
 #

def main():
    settings = get_project_settings()

    process = CrawlerProcess(settings)
    if not settings.getbool("AI_MODE"):
        process.crawl(BreezySpider)
        process.crawl(GenTechSpider)
        process.crawl(TietoSpider)
    else:
        process.crawl(BreezyAISpider)
        process.crawl(GenTechAISpider)
        process.crawl(TietoAISpider)
    process.start()


if __name__ == '__main__':
    main()