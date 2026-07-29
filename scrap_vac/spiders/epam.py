import scrapy

from scrap_vac.spiders.common import MixinHtml2Text


class EpamSpider(MixinHtml2Text, scrapy.Spider):
    name = "epam"
    allowed_domains = ["careers.epam.com"]
    start_urls = ["https://careers.epam.com/ua/jobs/ukraine"]

    def start_requests(self):
        self.logger.info(f"Starting {self.name}")
        yield scrapy.Request(
            url="https://careers.epam.com/api/jobs/v2/search/"
            "careers-i18n"
            "?facets=country%3D4000741334650021875"
            "&from=0"
            "&lang=uk%2Cen"
            "&size=1"
            "&sortBy=relevance%3Brelocation%3Dasc"
            "&websiteLocale=uk-ua",
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
                "Accept": "*/*",
                "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            },
        )

    def parse(self, response):
        data = response.json()["data"]
        total = data.get("total")
        from_ = 0
        size = 40
        self.logger.info(
            "Founded : {} vacancies, start scraping with butch {}".format(total, from_)
        )
        while from_ < total:
            yield scrapy.Request(
                url=f"https://careers.epam.com/api/jobs/v2/search/"
                f"careers-i18n"
                f"?facets=country%3D4000741334650021875"
                f"&from={from_}"
                f"&lang=uk%2Cen"
                f"&size={size}"
                f"&sortBy=relevance%3Brelocation%3Dasc"
                f"&websiteLocale=uk-ua",
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
                    "Accept": "*/*",
                    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                },
                callback=self.parse_json_data,
            )
            from_ += size

    def parse_json_data(self, response):
        jobs = response.json()["data"]["jobs"]
        for job in jobs:
            parsed_data = self.parse_job_data(job)
            if parsed_data:
                yield parsed_data

    def parse_job_data(self, job: dict) -> dict | None:

        if job.get("is_expired"):
            return None
        description_list = []
        if seo := job.get("seo"):
            if title := seo.get("title"):
                title = title.replace("/", " ")
            else:
                if name := job.get("name"):
                    title = name.replace("/", " ")
                else:
                    title = "No title"
            query_link = seo.get("url")
            if not query_link:
                return None
        else:
            return None

        if text := job.get("text"):
            description_list.append(text)

        category = job.get("category")
        requirements = None
        nice_to_have = None
        if category:
            if requirements_list := category.get("requirements"):
                requirements = "\n".join(requirements_list)
                description_list.append(f"requirements:\n {requirements}")

            if nice_to_have_list := category.get("nice_to_have"):
                nice_to_have = "\n".join(nice_to_have_list)
                description_list.append(f"nice_to_have:\n {nice_to_have}")

            if responsibility_list := category.get("responsibilities"):
                responsibilities = "\n".join(responsibility_list)
                description_list.append(f"responsibilities:\n {responsibilities}")

        if benefits_list := job.get("benefits"):
            if content := benefits_list[0].get("content"):
                description_list.append(f"benefits:\n {self.to_markdown(content)}")

        description = "\n\n".join(description_list).strip()
        seniority = job.get("seniority")

        return {
            "source": self.name,
            "title": title,
            "url": "https://careers.epam.com" + query_link,
            "description_text": description if description else None,
            "requirements": requirements,
            "nice_to_have": nice_to_have,
            "seniority": str(seniority) if seniority else None,
        }
