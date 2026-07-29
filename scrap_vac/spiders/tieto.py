import scrapy
from scrapy.http import Response

from scrap_vac.spiders.common import MixinHtml2Text


class TietoSpider(MixinHtml2Text, scrapy.Spider):
    """
    AI-mode version of Tieto spider.
    Collects vacancy data and defers relevance filtering to AI/rules layer.
    """

    name = "tieto"
    allowed_domains = ["careers.tieto.com"]
    start_urls = ["https://careers.tieto.com/jobs?options=193%2C403"]

    def parse(self, response: Response):
        for box in response.css(".attrax-vacancy-tile"):
            title = self._normalize_ws(box.css("a::text").get(""))
            listing_context = self._normalize_ws(
                " ".join(box.css("p::text, span::text").getall())
            )
            href = box.css("a::attr(href)").get()
            if not href:
                continue
            link = response.urljoin(href)
            yield scrapy.Request(
                link,
                callback=self.parse_details,
                meta={"title": title, "listing_context": listing_context},
            )

        next_exists = response.css('a[aria-label="Next pagination page"]')
        if next_exists:
            num_current_page = int(
                response.css(".attrax-pagination__page-item--current")
                .css("a::text")
                .get()
                .strip()
            )
            next_page = num_current_page + 1
            self.logger.info("Next page: %s", next_page)
            yield scrapy.Request(
                url=self.start_urls[0] + f"&page={next_page}",
                callback=self.parse,
            )

    def parse_details(self, response: Response):
        description = self.to_markdown(
            response.css('div[aria-label="Job description"]').get()
        )
        yield {
            "source": "tieto",
            "title": response.meta.get("title", ""),
            "url": response.url,
            "listing_context": response.meta.get("listing_context", ""),
            "description_text": description,
        }

    @staticmethod
    def _normalize_ws(value: str) -> str:
        return " ".join(value.split()).strip()
