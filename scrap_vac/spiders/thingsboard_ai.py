import scrapy

from scrap_vac.spiders.common import MixinCommonSpider


class ThingsboardAiSpider(MixinCommonSpider, scrapy.Spider):
    name = "thingsboard_ai"
    allowed_domains = ["thingsboard.io"]
    start_urls = ["https://thingsboard.io/careers/"]

    def parse(self, response):
        boxes = response.css(".cars-box")
        for box in boxes:
            href = box.css("a::attr(href)").get()
            yield response.follow(href, callback=self.parse_detail_page)

    def parse_detail_page(self, response):
        yield {
            "source": self.name,
            "title": response.css(".vacancy-head").css("h1::text").get(),
            "url": response.url,
            "description_text": self.extract_and_clean_all_text(response, "job-section"),
        }

