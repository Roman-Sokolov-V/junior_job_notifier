import scrapy

from scrap_vac.spiders.common import MixinHtml2Text


class SvitlaSpider(MixinHtml2Text, scrapy.Spider):
    name = "svitla"
    allowed_domains = ["svitla.com"]
    start_urls = ["https://svitla.com/career/?country=UA"]

    async def start(self):
        yield scrapy.Request(
            url="https://svitla.com/career/api/v1/jobs?page=1&country=UA",
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
                "Accept": "application/json",
                "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Referer": "https://svitla.com/career/?country=UA",
            },
            callback=self.parse,
        )

    def parse(self, response):
        data = response.json()
        items = data["items"]
        for item in items:
            slug = item.get("slug")
            if not slug:
                continue
            url = f"https://svitla.com/career/job/{slug}"
            position: str = item.get("position", "")
            sections: list = item.get("sections") or []

            def normalize_title(t: str) -> str:
                return t.strip().rstrip(":").strip().lower()

            sections_dict = {
                normalize_title(section["title"]): section.get("singleColumnContent")
                or ""
                for section in sections
            }

            blocks = []
            if description := self.to_markdown(item.get("fullDescription")):
                blocks.append(f"## Role overview\n{description}")

            if requirements := self.to_markdown(sections_dict.get("requirements")):
                blocks.append(f"## Requirements\n{requirements}")

            if nice_to_have := self.to_markdown(sections_dict.get("nice to have")):
                blocks.append(f"## Nice to have\n{nice_to_have}")

            if responsibilities := self.to_markdown(
                sections_dict.get("responsibilities")
            ):
                blocks.append(f"## Responsibilities\n{responsibilities}")

            full_description = "\n\n".join(blocks) if blocks else None
            yield {
                "source": self.name,
                "title": position,
                "url": url,
                "description_text": full_description,
                "requirements": requirements,
                "nice_to_have": nice_to_have,
            }
