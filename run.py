"""Entry point: crawl all spiders, filter matches, send notifications.

Import order in this file is NOT arbitrary — see inline comments.
Sections below must stay in this relative order:
  1. stdlib
  2. env setup (must precede any import that reads env vars or spins up
     CPU-parallel libraries)
  3. Twisted reactor installation (must precede importing twisted.internet
     .reactor / scrapy.crawler — see comment below)
  4. everything else (third-party, then local)
"""

# --- 1. Stdlib -----------------------------------------------------------
import gc
import logging
import os
from datetime import datetime, timedelta

# --- 2. Environment setup (must run before heavier imports) --------------
# python-dotenv must load .env before any local module that reads env vars
# at import time (e.g. db.session reading DATABASE_URL).
from dotenv import load_dotenv

load_dotenv()

# Обмежуємо внутрішню паралелізацію CPU-бібліотек (OpenMP/MKL/tokenizers),
# які використовує sentence-transformers. Без цього на завершенні процесу
# лишались "leaked semaphore" від пулу воркерів і скрипт міг зависати
# перед виходом. На CI (2 ядра) паралелізація й так майже не дає виграшу.
# Must be set before `sentence_transformers` (and its torch/tokenizers
# dependencies) are imported below.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["MKL_NUM_THREADS"] = "1"

# --- 3. Twisted reactor installation (order-critical) ---------------------
# КРИТИЧНО: спершу читаємо settings і встановлюємо потрібний reactor
# (у нас TWISTED_REACTOR = asyncio-based, потрібен для playwright/async
# spider'ів), і лише ПІСЛЯ цього імпортуємо twisted.internet.reactor /
# scrapy.crawler. Якщо імпортувати reactor раніше — Twisted встигає
# підняти дефолтний (select-based) reactor, і подальша спроба підняти
# asyncio-reactor призводить до тихого зависання без жодної помилки
# в логах.
from scrapy.utils.project import get_project_settings  # noqa: E402
from scrapy.utils.reactor import install_reactor  # noqa: E402

_settings_for_reactor = get_project_settings()
install_reactor(
    _settings_for_reactor["TWISTED_REACTOR"],
    _settings_for_reactor.get("ASYNCIO_EVENT_LOOP"),
)

# --- 4. Everything else ----------------------------------------------------
# Third-party (safe to import only now that the reactor is installed)
from scrapy.crawler import CrawlerRunner  # noqa: E402
from scrapy.utils.log import configure_logging  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402
from twisted.internet import defer, reactor  # noqa: E402

# Local
from common_settings import current_model_name, setup_logging  # noqa: E402
from db.crud import (  # noqa: E402
    create_state,
    delete_vacancies_not_seen_since,
    get_last_run,
    get_vacancies_urls,
    mark_urls_as_seen,
    get_db_now,
)
from db.session import get_db  # noqa: E402
from filter.matching import filter_vacancies  # noqa: E402
from scrap_vac.spiders import (  # noqa: E402
    AndersonSpider,
    BreezySpider,
    ConversionRateSpider,
    EpamSpider,
    NewxelSpider,
    StarGlobalSpider,
    SvitlaSpider,
    ThingsboardSpider,
    TietoSpider,
)
from telegram.notification import start_notification  # noqa: E402


def create_ai_model(model_name: str) -> SentenceTransformer:
    model = SentenceTransformer(model_name)
    return model


# Легкі spider'и (без playwright/Chromium) — можна запускати паралельно.
LIGHT_SPIDERS = [
    BreezySpider,
    TietoSpider,
    ThingsboardSpider,
    StarGlobalSpider,
    ConversionRateSpider,
    EpamSpider,
    AndersonSpider,
    GenTechSpider,
    SvitlaSpider,
]

# Важкі spider'и (використовують playwright/Chromium) — запускаються по одному.
HEAVY_SPIDERS = [
    NewxelSpider,
]


def main(model: SentenceTransformer):
    configure_logging()
    settings = _settings_for_reactor
    with get_db() as db:
        existing_urls = set(get_vacancies_urls(db))

    settings["EXISTING_URLS"] = existing_urls
    settings["SEEN_EXISTING_URLS"] = set()
    settings["AI_MODEL_INSTANCE"] = model

    runner = CrawlerRunner(settings)

    @defer.inlineCallbacks
    def crawl_all():
        # спершу всі легкі spider'и одночасно (як і раніше — паралельно)
        yield defer.DeferredList(
            [runner.crawl(spider) for spider in LIGHT_SPIDERS],
            consumeErrors=True,
        )
        # потім важкі spider'и по черзі — кожен наступний стартує лише
        # після повного завершення попереднього (включно з закриттям Chromium)
        for spider in HEAVY_SPIDERS:
            yield runner.crawl(spider)

        reactor.stop()

    crawl_all()
    reactor.run()  # блокує виконання, поки crawl_all() не викличе reactor.stop()

    seen_existing_urls = settings["SEEN_EXISTING_URLS"]

    with get_db() as db:
        # оновлюємо last_seen_at для тих, що реально зустрілись
        mark_urls_as_seen(db, seen_existing_urls)
        now = get_db_now()
        stale_cutoff = now - timedelta(days=7)
        state = get_last_run(db)
        if state is None:
            create_state(db)
        else:
            if state.updated_at > now - timedelta(days=3):
                # видаляємо тільки ті, що не бачились довше певного порогу
                # враховуючи можливі перерви в запуску
                delete_vacancies_not_seen_since(db, stale_cutoff)
            state.updated_at = now


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    try:
        model = create_ai_model(current_model_name)
        main(model)
        filter_vacancies(model)
        start_notification()
    finally:
        del model
        gc.collect()