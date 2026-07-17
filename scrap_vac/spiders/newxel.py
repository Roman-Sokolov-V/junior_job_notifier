import scrapy
from scrapy_playwright.page import PageMethod
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from scrap_vac.spiders.common import MixinTextEditor


class NewxelSpider(MixinTextEditor, scrapy.Spider):
    name = "newxel"
    allowed_domains = ["newxel.com"]
    start_urls = ["https://newxel.com/career/"]

    async def start(self):
        yield scrapy.Request(
            url=self.start_urls[0],
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_load_state", "networkidle"),
                ]
            },
            callback=self.parse,
        )

    async def parse(self, response, **kwargs):
        page = response.meta["playwright_page"]
        max_clicks = 20
        for _ in range(max_clicks):
            button = page.locator(".career-bottom button")

            # перевіряємо, чи кнопка взагалі існує і видима
            count = await button.count()
            if count == 0:
                self.logger.debug("Кнопки більше немає, всі вакансії підвантажені")
                break

            try:
                await button.scroll_into_view_if_needed(timeout=3000)
                await page.wait_for_timeout(300)  # дати час доскролити/стабілізуватись
                await button.click(timeout=3000, force=True)
                await page.wait_for_timeout(1000)
            except PlaywrightTimeoutError as e:
                self.logger.info(f"Кнопка не клікабельна / зникла {e}")
                break
        content = await page.content()
        await page.close()
        sel = scrapy.Selector(text=content)
        items = sel.xpath('//div[@class="career-item"]')
        for item in items:
            href = item.css('a::attr(href)').extract_first()
            yield scrapy.Request(href, callback=self.parse_detail)
            break

    def parse_detail(self, response):
        listing_context = self.extract_and_clean_all_text(response, "career-single-info")
        title = response.xpath('//h1/text()').extract_first()
        description = self.extract_and_clean_all_text(response, "career-single-content")
        # Шукаємо в тексті окремі параграфи за ключевими фразами:
        what_we_expect_starts = description.find("What We Expect")
        requirements = None
        nice_to_have = None
        embedding_text = None
        if what_we_expect_starts != -1:
            end_offset = description[what_we_expect_starts:].find("Why This Role Is Worth Your Time")
            if end_offset != -1:
                what_we_expect_ends = what_we_expect_starts + end_offset
                what_we_expect = description[what_we_expect_starts + 14: what_we_expect_ends]
                must_have_starts = what_we_expect.find("Must-have")
                nice_to_have_starts = what_we_expect.find("Nice-to-have")

                if must_have_starts != -1 and nice_to_have_starts != -1:
                    requirements = what_we_expect[must_have_starts + 9: nice_to_have_starts].strip()
                    nice_to_have = what_we_expect[nice_to_have_starts + 12:].strip()
                    embedding_text = f"requirements: {requirements}\nnice_to_have: {nice_to_have}"

                elif must_have_starts != -1:
                    requirements = what_we_expect[must_have_starts + 9:].strip()
                    embedding_text = f"requirements: {requirements}"

        self.logger.debug("--- Requirements ---%s", requirements)
        self.logger.debug("--- Nice to have ---%s", nice_to_have)
        self.logger.debug("--- Embedding text ---%s", embedding_text)


        yield {
            "source": self.name,
            "title": title,
            "url": response.url,
            "description_text": description,
            "listing_context": listing_context,
            "requirements": requirements,
            "nice_to_have": nice_to_have,
            "embedding_text": embedding_text
        }