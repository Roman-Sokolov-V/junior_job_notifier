from datetime import datetime

import scrapy
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from langdetect import detect, LangDetectException
from scrapy import Selector


class MixinTextEditor():

    @staticmethod
    def _normalize_ws(value: str) -> str:
        """Trim and normalize whitespace to one-line text."""
        return " ".join(value.split()).strip()


    @staticmethod
    def normalize_text(text: str) -> str | None:
        text = text.replace("\n", "").replace("\t", "").strip()
        if text:
            return text
        return None


    @classmethod
    def clean_paragraphs(cls, paragraph_texts: list[str]) -> str:
        return " ".join([
            norm for p in paragraph_texts
            if (norm := cls.normalize_text(p)) is not None
        ])


    @classmethod
    def extract_and_clean_all_text(cls, response, main_block_class: str) -> str:
        paragraphs = response.css(f'.{main_block_class} ::text').getall()
        return  cls.clean_paragraphs(paragraphs)

    @staticmethod
    def html_to_text(html):
        if not html:
            return ""
        sel = Selector(text=html)
        texts = sel.xpath("//text()").getall()
        return "\n".join(t.strip() for t in texts if t.strip())

    @staticmethod
    def parse_pub_date(date_str: str):
        try:
            return datetime.strptime(date_str, "%d %B %Y")
        except (ValueError, TypeError):
            return None


class MixinLangDetect():
    @staticmethod
    def detect_language(text):
        if not text or len(text.strip()) < 20:
            return "unknown"
        try:
            return detect(text)
        except LangDetectException:
            return "unknown"




class CommonSpider(MixinTextEditor, scrapy.Spider):

    async def manage_add_content_click_button(self, page, button_selector: str):
        max_clicks = 20
        for _ in range(max_clicks):
            button = page.locator(button_selector)
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
        return content