import scrapy

from scrap_vac.spiders.common import MixinHtml2Text


class ThingsboardSpider(MixinHtml2Text, scrapy.Spider):
    name = "thingsboard"
    allowed_domains = ["thingsboard.io"]
    start_urls = ["https://thingsboard.io/careers/"]

    def parse(self, response):
        boxes = response.css(".cars-box")
        for box in boxes:
            href = box.css("a::attr(href)").get()
            yield response.follow(href, callback=self.parse_detail_page)

    def parse_detail_page(self, response):
        description = self.to_markdown(response.css(".vacancy").get())
        yield {
            "source": self.name,
            "title": response.css(".vacancy-head").css("h1::text").get(),
            "url": response.url,
            "description_text": description,
        }
