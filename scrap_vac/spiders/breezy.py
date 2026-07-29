import scrapy

from scrap_vac.spiders.common import MixinHtml2Text


class BreezySpider(MixinHtml2Text, scrapy.Spider):
    """
    Spider now focuses on data collection, not business filtering.
    We collect vacancy content (EN/UA possible) and defer matching logic
    to a separate AI/rules layer.
    """

    name = "breezy"
    allowed_domains = ["gen-tech.breezy.hr"]
    start_urls = ["https://gen-tech.breezy.hr/"]

    def parse(self, response):
        # Grab all vacancy cards from list page.
        boxes = response.css(".position.transition")
        for box in boxes:
            href = box.css("a::attr(href)").get()
            if href:
                # Keep list-level metadata (optional) for better ranking/filtering later.
                title = self._normalize_ws(box.css("h2::text").get(""))
                # NOTE: Different sources have different layouts. We store this as a single optional
                # string instead of a source-specific list of parts.
                listing_context = self._normalize_ws(
                    " ".join(box.css(".meta span::text").getall())
                )
                link = response.urljoin(href)
                self.logger.info("Found vacancy link: %s", link)
                yield scrapy.Request(
                    url=link,
                    callback=self.parse_detail_page,
                    meta={
                        "title": title,
                        "listing_context": listing_context,
                    },
                )

    def parse_detail_page(self, response):
        self.logger.info("detail_page: %s", response.url)

        description_html = response.css(".description").get()
        description = self.to_markdown(description_html)
        yield {
            "source": "breezy",
            "title": response.meta.get("title", "No Title"),
            "url": response.url,
            "listing_context": response.meta.get("listing_context", ""),
            "description_text": description,
        }

    @staticmethod
    def _normalize_ws(value: str) -> str:
        """Trim and normalize whitespace to one-line text."""
        return " ".join(value.split()).strip()
