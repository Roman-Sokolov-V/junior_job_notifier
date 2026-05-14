import re

import scrapy


class BreezySpider(scrapy.Spider):
    name = "breezy"
    allowed_domains = ["gen-tech.breezy.hr"]
    start_urls = ["https://gen-tech.breezy.hr/?&department=Development#positions"]

    def parse(self, response):
        hrefs = set(response.css('a[title="Apply"]::attr(href)').getall())
        for href in hrefs:
            link = response.urljoin(href)
            self.logger.info("---------------------------------------------Found link: %s", link)
            yield scrapy.Request(
                url=link,
                callback=self.parse_detail_page,
                meta={"source_url": link}
            )

    def parse_detail_page(self, response):
        self.logger.info("detail_page: %s", response.url)
        text = " ".join(response.css('p::text').getall())
        if re.search(r"junior", text, re.IGNORECASE) and re.search(r"python|пайтон", text, re.IGNORECASE):
            self.logger.info("match found")
            yield {"link": response.meta["source_url"]}
        else:
            self.logger.info("No matches found")
