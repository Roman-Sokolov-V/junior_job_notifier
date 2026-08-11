import scrapy
import json
from urllib.parse import urlencode

from scrap_vac.spiders.common import MixinHtml2Text


class SquadSpider(MixinHtml2Text, scrapy.Spider):
    name = "squad"
    allowed_domains = ["squad.tech"]

    # Use Zyte transparent mode (site may require JS rendering)
    custom_settings = {
        "ZYTE_API_TRANSPARENT_MODE": True,
        # keep downloads reasonably fast
        "DOWNLOAD_TIMEOUT": 30,
    }

    API_BASE = "https://squad.tech/api/v1/vacancies"

    # Headers derived from observed curl — keeps requests closer to browser
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en",
        "Connection": "keep-alive",
    }
    countries = "Ukraine"

    async def start(self):
        """Begin by calling the hidden API for page 0; use pageLimit reasonably high to reduce requests."""
        page = 0
        page_limit = 50
        params = urlencode(
            {"page": page, "pageLimit": page_limit, "countries": self.countries}
        )
        url = f"{self.API_BASE}?{params}"
        yield scrapy.Request(
            url,
            callback=self.parse_main_api,
            headers=self.DEFAULT_HEADERS,
            meta={"page": page, "pageLimit": page_limit},
        )

    def parse_main_api(self, response):
        """Parse JSON response from hidden API, follow detail pages and paginate."""
        try:
            data = json.loads(response.text)
        except Exception:
            self.logger.error("Failed to parse JSON from %s", response.url)
            return

        vacancies = data.get("vacancies") or []
        for v in vacancies:
            human = (
                v.get("humanReadableId")
                or v.get("humanRedabled")
                or v.get("human_readable_id")
            )
            title = v.get("title")
            if not human:
                continue
            # call detail API first to obtain 'features' HTML, then fetch HTML page with features in meta
            detail_api = f"https://squad.tech/api/v1/vacancies/details/{human}?identifierType=jobPostSlug"
            yield scrapy.Request(
                detail_api,
                callback=self.parse_detail_api,
                headers=self.DEFAULT_HEADERS,
                meta={"api_title": title},
            )

        # simple pagination: continue while we get pageLimit items
        page = response.meta.get("page", 0)
        page_limit = response.meta.get("pageLimit", 50)
        if len(vacancies) >= page_limit:
            next_page = page + 1
            params = urlencode(
                {
                    "page": next_page,
                    "pageLimit": page_limit,
                    "countries": self.countries,
                }
            )
            next_url = f"{self.API_BASE}?{params}"
            yield scrapy.Request(
                next_url,
                callback=self.parse_main_api,
                headers=self.DEFAULT_HEADERS,
                meta={"page": next_page, "pageLimit": page_limit},
            )

    def parse_detail_api(self, response):
        """Parse JSON from vacancy details API, extract 'features' HTML and attach parsed text to meta before requesting HTML page."""
        try:
            data = json.loads(response.text)
        except Exception:
            self.logger.error("Failed to parse detail JSON from %s", response.url)
            data = {}

        features_html = data.get("features")
        if features_html:
            # features_html may be string or list — reuse mixin to convert
            features_text = self.to_markdown(features_html)
        else:
            return
        human = response.meta.get("human")
        title = response.meta.get("api_title")

        detail_url = f"https://squad.tech/careers/{human}"
        yield {
            "source": self.name,
            "title": title,
            "url": detail_url,
            "description_text": features_text,
        }
