import scrapy
from scrapy.http import Response

possible = {"junior", "trainee", "python", "django", "drf", "fastapi", "scrapy", "backend", "back-end"}
impossible = {"middle", "senior"}



class TietoSpider(scrapy.Spider):
    name = "tieto"
    allowed_domains = ["careers.tieto.com"]
    base_url = "https://careers.tieto.com"
    start_urls = ["https://careers.tieto.com/jobs?options=193%2C403",]

    def parse(self, response: Response):
        for box in response.css(".attrax-vacancy-tile"):
            text = set(
                box.css("a::text").get("").lower().split()
            )
            if text.intersection(impossible):
                continue

            if not text.intersection(possible):
                continue

            yield {
                "link": self.base_url + box.css("a::attr(href)").get()
            }
        next_exists = response.css('a[aria-label="Next pagination page"]')

        if next_exists:
            num_current_page = int(
                response
                .css(".attrax-pagination__page-item--current")
                .css("a::text")
                .get()
                .strip()
            )
            yield scrapy.Request(
                url=self.start_urls[0] + f"&page={num_current_page + 1}",
                callback=self.parse
            )
