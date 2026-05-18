from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from scrap_vac.spiders.breezy import BreezySpider
from scrap_vac.spiders.gen_tech import GenTechSpider
from scrap_vac.spiders.tieto import TietoSpider


from dotenv import load_dotenv
load_dotenv()

def main():
    settings = get_project_settings()

    process = CrawlerProcess(settings)

    process.crawl(BreezySpider)
    process.crawl(GenTechSpider)
    process.crawl(TietoSpider)
    process.start()


if __name__ == '__main__':
    main()