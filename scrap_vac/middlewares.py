# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.exceptions import IgnoreRequest

import os
import random
import logging
from scrapy.exceptions import NotConfigured


class ScrapVacSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    async def process_start(self, start):
        # Called with an async iterator over the spider start() method or the
        # matching method of an earlier spider middleware.
        async for item_or_request in start:
            yield item_or_request

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class ScrapVacDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class SkipExistingUrlsMiddleware:
    """Пропуск скрапінгу вакансій які вже є у списку існуючих,
    з трекінгом того, які саме existing URLs зустрілись під час цього прогону."""
    def process_request(self, request, spider):
        existing_urls = spider.settings.get("EXISTING_URLS", set())
        seen_existing_urls = spider.settings.get("SEEN_EXISTING_URLS")
        if request.url in existing_urls:
            seen_existing_urls.add(request.url)
            raise IgnoreRequest(f"URL already exists: {request.url}")


class ProxyRotationMiddleware:
    """Middleware for rotating proxies to avoid IP blocking and rate limiting."""

    def __init__(self, settings):
        self.enabled = settings.getbool('PROXY_ROTATION_ENABLED', False)
        self.logger = logging.getLogger(__name__)

        if not self.enabled:
            raise NotConfigured("Proxy rotation is disabled")

        # Load proxies from environment variable or file
        proxy_list = settings.get('PROXY_LIST')
        if proxy_list:
            self.proxies = [p.strip() for p in proxy_list.split(',') if p.strip()]
        else:
            proxy_file = settings.get('PROXY_FILE', 'proxies.txt')
            try:
                with open(proxy_file, 'r') as f:
                    self.proxies = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                self.logger.warning(f"Proxy file {proxy_file} not found")
                self.proxies = []

        # Validate proxy format (basic check)
        self.proxies = [p for p in self.proxies if self._is_valid_proxy_format(p)]

        if not self.proxies:
            raise NotConfigured("No valid proxies configured for rotation")

        self.logger.info(f"Proxy rotation enabled with {len(self.proxies)} proxies")

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def _is_valid_proxy_format(self, proxy):
        """Basic validation of proxy format.
        Supports formats like:
        - host:port
        - http://host:port
        - https://host:port
        - http://user:pass@host:port
        - socks5://host:port
        """
        if not proxy or not isinstance(proxy, str):
            return False

        # Must contain a colon for port separation
        if ':' not in proxy:
            return False

        # Basic check - at least host and port parts
        parts = proxy.split(':')
        if len(parts) < 2:
            return False

        # Host part should not be empty
        host_part = parts[0]
        # Remove protocol prefix if present
        if '://' in host_part:
            host_part = host_part.split('://')[-1]
        if '@' in host_part:  # Handle user:pass@host format
            host_part = host_part.split('@')[-1]

        return len(host_part) > 0 and len(parts[-1]) > 0

    def process_request(self, request, spider):
        # Skip if request already has proxy set (e.g., from Playwright)
        if 'proxy' in request.meta:
            return None

        # Select random proxy
        proxy = random.choice(self.proxies)
        request.meta['proxy'] = proxy

        # Log proxy usage at debug level to avoid excessive logging
        self.logger.debug(f"Using proxy: {proxy} for {request.url}")
        return None