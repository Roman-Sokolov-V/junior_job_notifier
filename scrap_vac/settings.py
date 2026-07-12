# Scrapy settings for scrap_vac project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import os
from dotenv import load_dotenv
load_dotenv()

BOT_NAME = "scrap_vac"

SPIDER_MODULES = ["scrap_vac.spiders"]
NEWSPIDER_MODULE = "scrap_vac.spiders"

ADDONS = {}


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "scrap_vac (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Concurrency and throttling settings
#CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 1

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "scrap_vac.middlewares.ScrapVacSpiderMiddleware": 543,
#}



# додаю свій мідлвар який скіпає скрапінг вакансій урл яких вже є в бд
DOWNLOADER_MIDDLEWARES = {
    "scrap_vac.middlewares.SkipExistingUrlsMiddleware": 543,
}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    "scrap_vac.middlewares.ScrapVacDownloaderMiddleware": 543,
#}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html

# AI-режим: повне збереження вакансій для матчингу; Telegram після matcher (опційно).
ITEM_PIPELINES = {
    "scrap_vac.pipelines.PostgresPipeline": 300,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"

#################################################################
# for working with scrapy-playwright
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_BROWSER_TYPE = "firefox"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    #"timeout": 20 * 1000,  # 20 seconds
}
# PLAYWRIGHT_CDP_URL = "http://localhost:9222"
# PLAYWRIGHT_CDP_KWARGS = {
#     "slow_mo": 1000,
#     "timeout": 10 * 1000
# }
# PLAYWRIGHT_CONNECT_KWARGS = {
#     "slow_mo": 1000,
#     "timeout": 10 * 1000
# }
# PLAYWRIGHT_CONTEXTS = {
#     "foobar": {
#         "context_arg1": "value",
#         "context_arg2": "value",
#     },
#     "default": {
#         "context_arg1": "value",
#         "context_arg2": "value",
#     },
#     "persistent": {
#         "user_data_dir": "/path/to/dir",  # will be a persistent context
#         "context_arg1": "value",
#     },
# }
# PLAYWRIGHT_MAX_CONTEXTS = 8
# TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
#####################################################################
DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
