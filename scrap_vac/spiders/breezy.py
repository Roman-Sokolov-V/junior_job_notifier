import re

import scrapy


class BreezySpider(scrapy.Spider):
    name = "breezy"
    allowed_domains = ["gen-tech.breezy.hr"]
    start_urls = ["https://gen-tech.breezy.hr/?&department=Development#positions"]

    def parse(self, response):

        boxes = response.css('.position.transition')
        for box in boxes:
            href = box.css('a::attr(href)').get()
            if href:
                title = box.css('h2::text').get("") + " | " + " | ".join(box.css('.meta span::text').getall())
                link = response.urljoin(href)
                self.logger.info("---------------------------------------------Found link: %s", link)
                yield scrapy.Request(
                    url=link,
                    callback=self.parse_detail_page,
                    meta={"title": title}
                )

    def parse_detail_page(self, response):
        self.logger.info("detail_page: %s", response.url)
        text = " ".join(response.css('p::text').getall())
        if re.search(r"junior", text, re.IGNORECASE) and re.search(r"python|пайтон", text, re.IGNORECASE):
            self.logger.info("match found")
            yield {"title": response.meta["title"], "url": response.url}
        else:
            self.logger.info("No matches found")
