import scrapy
from scrapy.http import Response


class TietoAISpider(scrapy.Spider):
    """
    AI-mode version of Tieto spider.
    Collects vacancy data and defers relevance filtering to AI/rules layer.
    """

    name = "tieto_ai"
    allowed_domains = ["careers.tieto.com"]
    start_urls = ["https://careers.tieto.com/jobs?options=193%2C403"]
   # impossible = {"middle", "senior"} # todo remove in final version

    def start_requests(self):
        if not self.crawler.settings.getbool("AI_MODE"):
            return
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response: Response):
        for box in response.css(".attrax-vacancy-tile"):
            title = self._normalize_ws(box.css("a::text").get(""))
            # if set(title.lower().split()).intersection(self.impossible): # todo remove in final version
            #     self.logger.info("not junior vacancy") # todo remove in final version
            # else: # todo remove in final version
            #self.logger.info("maybe junior vacancy")
            listing_context = self._normalize_ws(" ".join(box.css("p::text, span::text").getall()))
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
                response.css(".attrax-pagination__page-item--current").css("a::text").get().strip()
            )
            next_page = num_current_page + 1
            self.logger.info("Next page: %s", next_page)
            yield scrapy.Request(
                url=self.start_urls[0] + f"&page={next_page}",
                callback=self.parse,
            )

    def parse_details(self, response: Response):
        description_text = self._extract_description(response)
        yield {
            "source": "tieto",
            "title": response.meta.get("title", ""),
            "url": response.url,
            "listing_context": response.meta.get("listing_context", ""),
            "description_text": description_text,
        }

    @staticmethod
    def _normalize_ws(value: str) -> str:
        return " ".join(value.split()).strip()

    def _extract_description(self, response: Response) -> str:
        blocks = response.css("section p::text, article p::text, .content p::text, p::text").getall()
        cleaned = [self._normalize_ws(text) for text in blocks if text and text.strip()]
        return "\n".join(cleaned)
