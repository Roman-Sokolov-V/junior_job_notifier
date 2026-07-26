import scrapy
from html2text import html2text


class SvitlaSpider(scrapy.Spider):
    name = "svitla"
    allowed_domains = ["svitla.com"]
    start_urls = ["https://svitla.com/career/?country=UA"]

    async def start(self):
        yield scrapy.Request(
            url='https://svitla.com/career/api/v1/jobs?page=1&country=UA',
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
                "Accept": "application/json",
                "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Referer": "https://svitla.com/career/?country=UA",
            },
            callback=self.parse
        )

    def parse(self, response):
        data = response.json()
        items = data["items"]
        for item in items:
            full_description: str = html2text(item.get('fullDescription', None)).strip()
            slug = item.get('slug')
            if not slug:
                continue
            url = f"https://svitla.com/career/job/{slug}"
            position: str = item.get('position', '')
            sections: list = item.get('sections') or []

            def normalize_title(t: str) -> str:
                return t.strip().rstrip(':').strip().lower()

            sections_dict = {
                normalize_title(section['title']): section.get('singleColumnContent') or ""
                for section in sections
            }

            requirements: str = html2text(sections_dict.get('requirements', "")).strip()
            nice_to_have: str = html2text(sections_dict.get('nice to have', "")).strip()
            # responsibilities: str = html2text(sections_dict.get('responsibilities', "")).strip()
            embedding_text = (requirements + " " + nice_to_have).strip()

            yield {
                "source": self.name,
                "title": position,
                "url": url,
                "description_text": full_description,
                #"seniority": seniority,
                "requirements": requirements if requirements else None,
                "nice_to_have": nice_to_have if nice_to_have else None,
                "embedding_text": embedding_text if embedding_text else None,
            }
