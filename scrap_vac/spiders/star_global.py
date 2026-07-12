import json

import scrapy
from scrapy import Selector


class StarGlobalSpider(scrapy.Spider):
    name = "star_global"
    allowed_domains = ["star.global"]
    start_urls = ["https://star.global/careers/?pageSlug=careers"]

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
        data = response.json()  # або json.loads(response.text)
        jobs = data["results"]
        for job in jobs:
            yield scrapy.Request(
                url=job.pop("url"),
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
                    "Accept": "application/json, text/plain, */*",
                    "Referer": "https://star.global/careers/?pageSlug=careers",
                    # If-None-Match НЕ передаємо — отримаємо 200 з даними
                },
                callback=self.parse_detail_page,
                cb_kwargs = {"job": job}
            )


    def parse_detail_page(self, response, job: dict):
        raw = response.css('#__NEXT_DATA__::text').get()
        data = json.loads(raw)

        queries = data['props']['pageProps']['dehydratedState']['queries']
        job_data = queries[1]['state']['data']  # індекс 1 — дані вакансії

        html_content = job_data['content']['attrs']['html']
        sel = Selector(text=html_content)
        description = '\n'.join(sel.css('p::text, li::text').getall()).strip()
        job.pop("id")
        yield {
            "source": self.name,
            "title": job.pop("title"),
            "url": response.url,
            "description_text": description,
            "listing_context": str(job)
        }