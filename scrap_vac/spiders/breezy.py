import scrapy


class BreezySpider(scrapy.Spider):
    """
    Spider now focuses on data collection, not business filtering.
    We collect vacancy content (EN/UA possible) and defer matching logic
    to a separate AI/rules layer.
    """

    name = "breezy"
    allowed_domains = ["gen-tech.breezy.hr"]
    start_urls = ["https://gen-tech.breezy.hr/?&department=Development#positions"]


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
                listing_context = self._normalize_ws(" ".join(box.css(".meta span::text").getall()))
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

        description_text = self._extract_description(response)
        self.logger.info("description_text: %s", description_text)


        yield {
            "source": "breezy",
            "title": response.meta.get("title", "No Title"),
            "url": response.url,
            "listing_context": response.meta.get("listing_context", ""),
            "description_text": description_text,
            # через те що на цьому ресурсі нема сталої структури
            # неможливо відокремити текст для embedding_text
        }

    @staticmethod
    def _normalize_ws(value: str) -> str:
        """Trim and normalize whitespace to one-line text."""
        return " ".join(value.split()).strip()

    def _extract_description(self, response) -> str:
        """
        Best-effort content extraction.
        We take text from common content containers and fallback to all <p>.
        """
        blocks = response.css(
            "section p::text, article p::text, .description p::text, .content p::text"
        ).getall()
        if not blocks:
            blocks = response.css("p::text").getall()

        cleaned = [self._normalize_ws(text) for text in blocks if text and text.strip()]
        return "\n".join(cleaned)