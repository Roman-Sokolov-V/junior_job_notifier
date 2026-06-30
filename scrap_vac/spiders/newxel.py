import scrapy

from scrap_vac.spiders.common import MixinCommonSpider


class NewxelSpider(MixinCommonSpider, scrapy.Spider):
    name = "newxel"
    allowed_domains = ["newxel.com"]
    start_urls = ["https://newxel.com/career/"]

    def parse(self, response):
        items = response.xpath('//div[@class="career-item"]')
        for item in items:
            href = item.css('a::attr(href)').extract_first()
            yield scrapy.Request(href, callback=self.parse_detail)

    def parse_detail(self, response):
        listing_context = self.extract_and_clean_all_text(response, "career-single-info")
        title = response.xpath('//h1/text()').extract_first()
        description = self.extract_and_clean_all_text(response, "career-single-content")
        yield {
            "source": self.name,
            "title": title,
            "url": response.url,
            "description_text": description,
            "listing_context": listing_context
        }