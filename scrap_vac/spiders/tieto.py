import re

import scrapy
from scrapy.http import Response



class TietoSpider(scrapy.Spider):
    name = "tieto"
    allowed_domains = ["careers.tieto.com"]
    base_url = "https://careers.tieto.com"
    start_urls = ["https://careers.tieto.com/jobs?options=193%2C403",]
    possible = {"junior", "trainee", "python", "django", "drf", "fastapi", "scrapy", "backend", "back-end"}
    impossible = {"middle", "senior"}

    def parse(self, response: Response):
        response.css(".attrax-vacancy-tile a::text").getall()
        for box in response.css(".attrax-vacancy-tile"):
            title = box.css("a::text").get("")
            if set(title.lower().split()).intersection(self.impossible):
                self.logger.info("not junior vacancy")
            else:
                self.logger.info("maybe junior vacancy")
                href = box.css("a::attr(href)").get()
                link = response.urljoin(href)
                yield scrapy.Request(link, callback=self.parse_details, meta={"title": title})


        next_exists = response.css('a[aria-label="Next pagination page"]')

        if next_exists:
            num_current_page = int(
                response.css(".attrax-pagination__page-item--current").css("a::text").get().strip()
            )
            next_page = num_current_page + 1
            self.logger.info("Next page: %s", next_page)
            yield scrapy.Request(
                url=self.start_urls[0] + f"&page={next_page}",
                callback=self.parse
            )

    def parse_details(self, response: Response):
        text = " ".join(response.css("p::text").getall())
        if re.search(r"(python|пайтон)", text, re.IGNORECASE):
            self.logger.info("python vacancy found")
            yield {
                "title": response.meta["title"],
                "url": response.url,
            }
        else:
            self.logger.info("not python vacancy")
