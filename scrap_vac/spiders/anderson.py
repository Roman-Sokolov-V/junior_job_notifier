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
            name = job.pop("name")
            job.pop("hiringTag")
            job.pop("duration")
            job.pop("isHot")
            job.pop("matrix")
            url = "https://people.andersenlab.com/ua/vacancy/" + str(job.pop("vacancy_id"))
            yield {
                "source": self.name,
                "title": name,
                "url": url,
                "description_text": str(job),
            }
