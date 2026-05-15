import re
import scrapy
from scrapy.http import Response


class GenTechSpider(scrapy.Spider):
    name = "gen_tech"

    def start_requests(self):
        # input_id = '#Development-comp-m9h1cdvh-6'
        yield scrapy.Request(
            "https://www.gen.tech/career",
            meta={
                "playwright": True,
                "playwright_include_page": True,
                # "playwright_page_methods": [
                #     # 1. Чекаємо завантаження списку
                #     #PageMethod("wait_for_selector", 'div[role="listitem"]'),
                #
                #     # 2. Чекаємо чекбокс
                #     PageMethod("wait_for_selector", input_id),
                #
                #     # 3. Клікаємо по фільтру
                #     # 1. Скролимо до інпуту, щоб він був видимим
                #     PageMethod("evaluate", f'document.querySelector("{input_id}").scrollIntoView({{block: "center"}})'),
                #     PageMethod("wait_for_timeout", 1000),
                #
                #     # 2. Фокусуємося безпосередньо на інпуті
                #     PageMethod("focus", input_id),
                #
                #     # 3. Тиснемо ПРОБІЛ (Space)
                #     # Це змусить браузер перемкнути чекбокс і сповістити React так,
                #     # ніби це зробив користувач з клавіатури
                #     PageMethod("press", input_id, " "),
                #
                #
                #     # 4. КРИТИЧНО: Чекаємо, поки зникне індикатор завантаження або
                #     # оновиться список. На Wix краще почекати паузу або networkidle
                #     PageMethod("wait_for_load_state", "networkidle"),
                #
                #     # Додаткова страховка: чекаємо 2 секунди, поки React перемалює картки
                #     PageMethod("wait_for_timeout", 10000),
                #
                #     # Переконуємося, що після фільтрації хоча б одна картка є
                #     PageMethod("wait_for_selector", 'div[role="listitem"]'),
                #     # Робимо скріншот, щоб перевірити, чи вибрано фільтр
                #     PageMethod("screenshot", path="check_filter.png", full_page=True),
                # ],
            },
            callback=self.parse
        )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        content = await page.content()
        response = response.replace(body=content)
        boxes = response.css('div[role="listitem"].wixui-repeater__item')
        links_titles = []

        for box in boxes:
            title = " ".join(box.css(".wixui-rich-text__text::text").getall()).strip()
            if re.search(r"junior", title, re.IGNORECASE):
                link = box.css("a::attr(href)").get()
                if link:
                    links_titles.append((link, title))

        # check detail pages
        if not links_titles:
            self.logger.info("Links not found...")
        for link_title in links_titles:
            yield scrapy.Request(
                url=link_title[0],
                callback=self.parse_detail_page,
                meta={"title": link_title[1]}
            )

        # Pagination
        next_button_selector = 'button[data-hook="pagination.navigation-button.next"]:not([disabled])'

        # next_button = response.css(next_button_selector)
        is_next_active = await page.query_selector(next_button_selector)

        if is_next_active:
            self.logger.info("Натискаємо кнопку Next...")
            await page.click(next_button_selector)

            # Чекаємо на оновлення контенту
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)

            # Отримуємо оновлений контент сторінки
            content = await page.content()
            # Створюємо новий response з оновленим HTML
            new_response = response.replace(body=content)
            # Рекурсивно викликаємо parse для нової сторінки
            async for item in self.parse(new_response):
                yield item
        else:
            # Якщо кнопки немає або вона disabled — закриваємо сторінку
            await page.close()


    def parse_detail_page(self, response: Response):
        if text:= " ".join(response.css(".wixui-box p::text").getall()).strip():
            if re.search(r"(python|пайтон)", text, re.IGNORECASE):
                yield {"title": response.meta["title"], "url": response.url}
            else:
                self.logger.info("not python vacancy")
        else:
            self.logger.info("text not found...")
