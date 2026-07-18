import scrapy

from scrap_vac.spiders.common import CommonSpider


class SigmaTechnologySpider(CommonSpider):
    name = "sigma_technology"
    allowed_domains = ["sigmatechnology.com"]
    start_urls = ["https://sigmatechnology.com/open-positions/"]

    async def start(self):
        yield scrapy.Request(
            #url='https://sigmatechnology.com/wp-json/sigma_profiler/positions?query=&sort=publicationDate&lang=en&level=all&company%5B%5D=Sigma%20Technology%20China&company%5B%5D=Sigma%20Technology%20Consulting&company%5B%5D=Sigma%20Technology%20Development&company%5B%5D=Sigma%20Technology%20Group&company%5B%5D=Sigma%20Technology%20Hungary&company%5B%5D=Sigma%20Technology%20Information&company%5B%5D=Sigma%20Technology%20Mid&company%5B%5D=Sigma%20Technology%20Solutions&company%5B%5D=Sigma%20Technology%20Systems&company%5B%5D=Sigma%20Technology%20USA&company%5B%5D=Sigma%20Technology&company%5B%5D=Sigma%20Technology%20Transformation&company%5B%5D=Sigma%20Technology%20Insights&company%5B%5D=Sigma%20Technology%20Digital%20%26%20Cloud%20Solutions&company%5B%5D=Sigma%20Technology%20Innovation&company%5B%5D=Sigma%20Technology%20Norway&company%5B%5D=Sigma%20Technology%20Embedded%20Solutions&company%5B%5D=Sigma%20Technology%20IT%20Infra&company%5B%5D=Sigma%20Technology%20Cloud&company%5B%5D=Sigma%20Technology%20Tech%20Network&company%5B%5D=Sigma%20Technology%20Software%20Solutions&company%5B%5D=Sigma%20Technology%20Informatics%20Solutions&company%5B%5D=Sigma%20Technology%20Experience&company%5B%5D=Sigma%20Technology%20Digital%20Solutions&company%5B%5D=Sigma%20Technology%20Tech%20House&company%5B%5D=Sigma%20Technology%20North%20Solutions&company%5B%5D=Sigma%20Technology%20Embedded%20Network&company%5B%5D=Sigma%20Technology%20Systems%20Norway&company%5B%5D=Sigma%20Technology%20ERP%20Advisory&company%5B%5D=Sigma%20Technology%20Engineering&company%5B%5D=Sigma%20Technology%20Elevate&competence=&country=&city=',
            # вище те що показує сайт, нижче прибрані фільтри за компаніями, вакансій більше, хоча можливо
            # не всі будуть релевантні, хто зна чому на сайті застосовані ті фільтри
            url=(
                'https://sigmatechnology.com/wp-json/sigma_profiler/positions'
                '?query=&sort=publicationDate&lang=en&level=all'
                '&competence=&country=&city='
            ),
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
                "Accept": "*/*",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://sigmatechnology.com/open-positions/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            },
            callback=self.parse,
        )

    async def parse(self, response):
        data = response.json()  # або json.loads(response.text)
        total = data.get("total")
        self.logger.info(total)
        vacancies: list[dict] = data.get("data")
        for vacancy in vacancies:
            # фільтрація за мовою, тут багато шведської і норвежської
            language = self.detect_language(vacancy.get("description"))
            if language not in  ("en", "uk", "ukr"):
                continue

            description = self.html_to_text(vacancy.get("description", ""))
            qualifications = self.html_to_text(vacancy.get("qualifications", ""))
            experience = self.html_to_text(vacancy.get("experience", ""))
            offer = self.html_to_text(vacancy.get("offer", ""))
            country = vacancy.get("country", "")
            cities = vacancy.get("cities", "")
            full_description = f"Summary: {description}.\n Qualifications: {qualifications}.\n Experience: {experience}.\n Offer: {offer} "
            requirements = ((qualifications + " ") if qualifications else "") + experience

            yield {
                "source": self.name,
                "title": vacancy.get("title"),
                "url": vacancy.get("link"),
                "description": vacancy.get("description") ,
                "description_text": full_description,
                "listing_context": f"Country: {country}, Cities: {cities}",
                "requirements": requirements if requirements else None,
                "embedding_text": qualifications if qualifications  else None,
                "country": vacancy.get("country", None),
            }
