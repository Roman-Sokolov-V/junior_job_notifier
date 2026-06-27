import re
import scrapy
from scrapy.http import Response


class GenTechAISpider(scrapy.Spider):
    """
    AI-mode version of GenTech spider.
    Collects vacancy data without hardcoded junior/python filtering.
    """

    name = "gen_tech_ai"

    def start_requests(self):

        if not self.crawler.settings.getbool("AI_MODE"):
            return
        yield scrapy.Request(
            "https://www.gen.tech/career",
            meta={
                "playwright": True,
                "playwright_include_page": True,
            },
            callback=self.parse,
        )

    async def parse(self, response: Response):
        page = response.meta["playwright_page"]
        content = await page.content()
        response = response.replace(body=content)

        boxes = response.css('div[role="listitem"].wixui-repeater__item')
        links_titles = []

        for box in boxes:
            title = self._normalize_ws(" ".join(box.css(".wixui-rich-text__text::text").getall()))
            listing_context = self._normalize_ws(" ".join(box.css("span::text, p::text").getall()))

            if re.search(r"junior", title, re.IGNORECASE): # todo remove in final version
                link = box.css("a::attr(href)").get()
                if link:
                    links_titles.append((link, title, listing_context))

        if not links_titles:
            self.logger.info("Links not found...")

        for link, title, listing_context in links_titles:
            yield scrapy.Request(
                url=link,
                callback=self.parse_detail_page,
                meta={"title": title, "listing_context": listing_context},
            )

        next_button_selector = 'button[data-hook="pagination.navigation-button.next"]:not([disabled])'
        is_next_active = await page.query_selector(next_button_selector)

        if is_next_active:
            self.logger.info("Clicking Next...")
            await page.click(next_button_selector)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)

            content = await page.content()
            new_response = response.replace(body=content)
            async for item in self.parse(new_response):
                yield item
        else:
            await page.close()

    def parse_detail_page(self, response: Response):
        description_text = self._extract_description(response)
        yield {
            "source": "gen_tech",
            "title": response.meta.get("title", ""),
            "url": response.url,
            "listing_context": response.meta.get("listing_context", ""),
            "description_text": description_text,
        }

    @staticmethod
    def _normalize_ws(value: str) -> str:
        return " ".join(value.split()).strip()

    def _extract_description(self, response: Response) -> str:
        blocks = response.css("section p::text, article p::text, .wixui-box p::text, p::text").getall()
        cleaned = [self._normalize_ws(text) for text in blocks if text and text.strip()]
        return "\n".join(cleaned)
