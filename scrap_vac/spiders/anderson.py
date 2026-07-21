from pprint import pprint

import scrapy



class AndersonSpider(scrapy.Spider):
    name = "anderson"
    allowed_domains = ["people.andersenlab.com", "asite-api.andersenlab.com"]
    start_urls = ["https://people.andersenlab.com/ua/vacancies"]

    def start_requests(self):
        yield scrapy.Request(
            url="https://asite-api.andersenlab.com/api/integration/recruitment/vacancies",
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
                "Accept": "*/*",
                "Accept-Language": "ua",
                "Referer": "https://people.andersenlab.com/",
                "Api-Version": "v5",
                "Content-Type": "application/json",
                "X-Country-Code": "UA",
                "Origin": "https://people.andersenlab.com",
            },
            callback=self.parse
        )

    def parse(self, response):
        jobs = response.json()
        for job in jobs:

            vacancy_id = job.get("vacancy_id")
            if not vacancy_id:
                continue
            name = job.get("name", str(vacancy_id))
            url = "https://people.andersenlab.com/ua/vacancy/" + str(vacancy_id)
            nice_to_have = ""
            if nice_to_have_key := job.get("niceToHave"):
                if nice_to_have_dict := nice_to_have_key[0]:
                    if nice_to_have_list := nice_to_have_dict.get("content"):
                        nice_to_have = ", ".join(nice_to_have_list)
            seniority = job.get("level", None)
            requirements = ""
            if requirements_key := job.get("requirements"):
                if requirements_dict := requirements_key[0]:
                    if requirements_list := requirements_dict.get("content"):
                        requirements = ", ".join(requirements_list)
            embedding_text = (requirements + " ") if requirements + nice_to_have else ""

            responsibilities = ""
            if responsibilities_key := job.get("responsibilities"):
                if responsibilities_dict := responsibilities_key[0]:
                    if responsibilities_list := responsibilities_dict.get("content"):
                        responsibilities = ", ".join(responsibilities_list)
            description_text = (
                (("requirements: " + requirements + "\n") if requirements else "")
                + (("nice_to_have: " + nice_to_have + "\n") if nice_to_have else "")
                + (("responsibilities: " + responsibilities) if responsibilities else "")
            )

            yield {
                "source": self.name,
                "title": name,
                "url": url,
                "description_text": description_text if description_text else None,
                "seniority": seniority,
                "requirements": requirements if requirements else None,
                "nice_to_have": nice_to_have if nice_to_have else None,
                "embedding_text": embedding_text if embedding_text else None,
            }
