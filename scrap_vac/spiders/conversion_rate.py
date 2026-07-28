import scrapy

from scrap_vac.spiders.common import MixinHtml2Text


class ConversionRateSpider(MixinHtml2Text, scrapy.Spider):
    name = "conversion_rate"
    allowed_domains = ["conversionrate.store"]
    start_urls = ["https://conversionrate.store/career/"]

    def parse(self, response):
        self.logger.debug("__________________Parsing vacancy listing")
        jobs_items = response.css(".jobs__item")
        for job_item in jobs_items:
            href = job_item.css("a::attr(href)").extract_first()
            self.logger.debug("___________________href {}".format(href))
            yield response.follow(href, callback=self.parse_job)

    def parse_job(self, response):

        self.logger.debug("___________________Parsing detail vacancy")

        title = response.css(".vacancy__title::text").extract_first()
        listing_context = self.to_markdown(response.css(".vacancy__option").get())
        description = self.to_markdown(response.css(".vacancy__info").get())

        yield {
            "source": self.name,
            "url": response.url,
            "title": title,
            "description_text": description,
            "listing_context": listing_context,
        }
