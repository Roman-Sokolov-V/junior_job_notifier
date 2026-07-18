import scrapy
from pprint import pprint

from scrap_vac.spiders.common import MixinTextEditor


class EpamSpider(MixinTextEditor, scrapy.Spider):
    name = "epam"
    allowed_domains = ["careers.epam.com"]
    start_urls = ["https://careers.epam.com/ua/jobs/ukraine"]

    def start_requests(self):
        self.logger.info(f"Starting {self.name}")
        yield scrapy.Request(
            url= 'https://careers.epam.com/api/jobs/v2/search/'
                 'careers-i18n'
                 '?facets=country%3D4000741334650021875'
                 '&from=0'
                 '&lang=uk%2Cen'
                 '&size=1'
                 '&sortBy=relevance%3Brelocation%3Dasc'
                 '&websiteLocale=uk-ua',
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0',
                'Accept': '*/*',
                'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin'
            }
        )

    def parse(self, response):
        data = response.json()["data"]
        total = data.get("total")
        from_ = 0
        size = 40
        self.logger.info("Founded : {} vacancies, start scraping with butch {}".format(total, from_))
        while from_ < total:
            yield scrapy.Request(
                url=f'https://careers.epam.com/api/jobs/v2/search/'
                    f'careers-i18n'
                    f'?facets=country%3D4000741334650021875'
                    f'&from={from_}'
                    f'&lang=uk%2Cen'
                    f'&size={size}'
                    f'&sortBy=relevance%3Brelocation%3Dasc'
                    f'&websiteLocale=uk-ua',
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0',
                    'Accept': '*/*',
                    'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin'
                },
                callback=self.parse_json_data

            )
            from_ += size

    def parse_json_data(self, response):

        data = response.json()["data"]
        pprint(data)
        pprint(data.keys())
        jobs = response.json()["data"]["jobs"]
        pprint(jobs)
        skipped_counter = 0
        scrapped_counter = 0
        for job in jobs:
            title = None
            url = None
            description = None
            requirements = None
            nice_to_have = None
            if is_expired := job.get("is_expired"):
                skipped_counter += 1
                continue

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
                    skipped_counter += 1
                    continue
                url = "https://careers.epam.com" + query_link
                description_list = []
                embedding_list = []
                text = job.get("text", "")
                description_list.append(text)

                benefits_list = job.get("benefits")
                if benefits_list:
                    content = benefits_list[0].get("content")
                    if content:
                        description_list.append(f"benefits: {self.html_to_text(content)}")

                category = job.get("category")
                if category:
                    requirements_list = job.get("requirements")
                    if requirements_list:
                        requirements = ", ".join(requirements_list)
                        description_list.append(f"requirements: {requirements}")
                        embedding_list.append(f"requirements: {requirements}")
                    nice_to_have_list = category.get("nice_to_have")
                    if nice_to_have_list:
                        nice_to_have = ", ".join(nice_to_have_list)
                        description_list.append(f"nice_to_have: {nice_to_have}")
                        embedding_list.append(f"nice_to_have: {nice_to_have}")
                    responsibility_list = job.get("responsibility")
                    if responsibility_list:
                        responsibilities = ", ".join(responsibility_list)
                        description_list.append(f"responsibilities: {responsibilities}")
                        embedding_list.append(f"responsibility: {responsibility_list[0]}")

                disclaimers_list = job.get("disclaimers")
                if disclaimers_list:
                    contents_list = []
                    for disclaimer in disclaimers_list:
                        content_html = disclaimer.get("content")
                        if content_html:
                            content = self.html_to_text(content_html)
                            contents_list.append(content)
                    disclaimer_content = "\n\n".join(contents_list)
                    description_list.append(f"disclaimers: {disclaimer_content}")
            description = "\n\n".join(description_list)
            embedding_text = " ".join(embedding_list)
            scrapped_counter += 1
            yield {
                "source": self.name,
                "title": title,
                "url": url,
                #"description_text": description,
                "description_text": embedding_text, # todo change
                "embedding_text": embedding_text,
                "requirements": requirements,
                "nice_to_have": nice_to_have,
            }


