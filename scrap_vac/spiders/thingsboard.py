import scrapy

from scrap_vac.spiders.common import MixinTextEditor


class ThingsboardSpider(MixinTextEditor, scrapy.Spider):
    name = "thingsboard"
    allowed_domains = ["thingsboard.io"]
    start_urls = ["https://thingsboard.io/careers/"]

    def parse(self, response):
        boxes = response.css(".cars-box")
        for box in boxes:
            href = box.css("a::attr(href)").get()
            yield response.follow(href, callback=self.parse_detail_page)

    def parse_detail_page(self, response):
        all_raw_text = response.css(".vacancy").xpath('.//text()').getall()
        if not all_raw_text:
            all_raw_text = response.xpath('//body//text()').getall()

        all_clean_text = "\n".join([t.strip() for t in all_raw_text if t.strip()])
        xpath_query = (
            '//div[contains(@class, "job-section")]'
            '[.//*[self::h2 or self::h3][contains(translate(text(), "REQUIMNTS", "requimnts"), "requirements")]]'
            '//text()'
        )
        requirements_row = response.xpath(xpath_query).getall()
        requirements = self.clean_paragraphs(requirements_row)
        xpath_query = (
            '//div[contains(@class, "job-section")]'
            '[.//*[self::h2 or self::h3][contains(translate(text(), "NICETHV", "nicethv"), "nice to have")]]'
            '//text()'
        )
        nice_to_have_row = response.xpath(xpath_query).getall()
        nice_to_have = self.clean_paragraphs(nice_to_have_row)
        embedding_text = "Requirements : " + requirements if requirements else ""
        embedding_text = embedding_text + "\n" + "Nice to have: " + nice_to_have if nice_to_have else embedding_text

        yield {
            "source": self.name,
            "title": response.css(".vacancy-head").css("h1::text").get(),
            "url": response.url,
            "description_text": all_clean_text,
            "requirements": requirements,
            "embedding_text": embedding_text,
            "nice_to_have": nice_to_have,
        }

