import scrapy

from scrap_vac.spiders.common import MixinCommonSpider


class ConversionRateSpider(MixinCommonSpider, scrapy.Spider):
    name = "conversion_rate"
    allowed_domains = ["conversionrate.store"]
    start_urls = ["https://conversionrate.store/career/"]

    def parse(self, response):
        self.logger.info("__________________Parsing vacancy listing")
        jobs_items = response.css(".jobs__item")
        for job_item in jobs_items:
            href = job_item.css('a::attr(href)').extract_first()
            self.logger.debug("___________________href {}".format(href))
            yield response.follow(href, callback=self.parse_job)

    def parse_job(self, response):
        self.logger.info("___________________Parsing detail vacancy")
        title = response.css(".vacancy__title::text").extract_first()
        listing_context = self.extract_and_clean_all_text(response, "vacancy__option")
        description = self.extract_and_clean_all_text(response, "vacancy__info")
        yield {
            "source": self.name,
            "url": response.url,
            "title": title,
            "description_text": description,
            "listing_context": listing_context,
        }
