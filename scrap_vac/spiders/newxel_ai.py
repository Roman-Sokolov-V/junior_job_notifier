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