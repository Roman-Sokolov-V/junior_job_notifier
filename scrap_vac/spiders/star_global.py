import json
from pprint import pprint

import scrapy
from scrapy import Selector

from scrap_vac.spiders.common import CommonSpider


class StarGlobalSpider(CommonSpider):
    name = "star_global"
    allowed_domains = ["star.global"]
    #start_urls = ["https://star.global/careers/?pageSlug=careers"]

    def start_requests(self):
        yield scrapy.Request(
            url="https://star.global/api/job-teasers/?post_type=job&lang=en",
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://star.global/careers/?pageSlug=careers",
                # If-None-Match НЕ передаємо — отримаємо 200 з даними
            },
            callback=self.parse_jobs,
        )

    def parse_jobs(self, response):
        data = response.json()
        jobs = data["results"]
        for job in jobs:
            context = f"work type: {job['work_type'].get("name")}", f"location: {job['location'].get('label')}"
            title = job.get("title")

            yield scrapy.Request(
                url=job.get("url"),
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
                    "Accept": "application/json, text/plain, */*",
                    "Referer": "https://star.global/careers/?pageSlug=careers",
                    # If-None-Match НЕ передаємо — отримаємо 200 з даними
                },
                callback=self.parse_detail_page,
                cb_kwargs = {"context": context, "title": title}
            )


    def parse_detail_page(self, response, context: str, title: str):
        all_raw_text = response.xpath('//div[contains(., "looking for you")]//text()').getall()
        if not all_raw_text:
            all_raw_text = response.xpath('//body//text()').getall()

        all_clean_text = "\n".join([t.strip() for t in all_raw_text if t.strip()])

        # 2. Витягуємо блок "Skills" за допомогою Python (100% стабільно)
        skills_clean_text = None

        # Знаходимо всі h2 на сторінці
        h2_elements = response.xpath('//h2')

        for h2 in h2_elements:
            # Отримуємо текст самого заголовка
            h2_text = "".join(h2.xpath('.//text()').getall()).lower()

            # Якщо знайшли заголовок зі словом "skills" або "experience"
            if "skills" in h2_text and "experience" in h2_text:
                # Забираємо текст усіх наступних елементів-сусідів
                siblings_text = []
                for sibling in h2.xpath('./following-sibling::*'):
                    # Якщо наткнулися на наступний h2 — зупиняємо збір тексту
                    if sibling.root.tag == 'h2':
                        break

                    # Збираємо текст з поточного елемента (абзацу чи списку)
                    text_nodes = sibling.xpath('.//text()').getall()
                    clean_nodes = [t.strip() for t in text_nodes if t.strip()]
                    if clean_nodes:
                        siblings_text.extend(clean_nodes)

                skills_clean_text = "\n".join(siblings_text)
                break

        yield {
            "source": self.name,
            "title": title,
            "url": response.url,
            "description_text": all_clean_text,
            "listing_context": context,
            "requirements": skills_clean_text,
            "embedding_text": skills_clean_text,
        }