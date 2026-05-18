# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import psycopg2
from scrapy.exceptions import DropItem
import requests
from scrapy.exceptions import NotConfigured


# class ScrapVacPipeline:
#     def process_item(self, item, spider):
#
#         return item


class PostgresPipeline:
    def __init__(self, db_url):
        self.db_url = db_url

    @classmethod
    def from_crawler(cls, crawler):
        # цей метод запускається першим
        # Отримуємо URL бази з settings.py або env
        return cls(
            db_url=crawler.settings.get('DATABASE_URL')
        )  # створюєм екземпляр класу з db_url = settings.get('DATABASE_URL')

    def open_spider(self, spider):
        # цей метод запускається другим
        # Підключаємось при старті
        self.conn = psycopg2.connect(self.db_url)
        self.cur = self.conn.cursor()
        # Створюємо таблицю, якщо її нема
        self.cur.execute("""
                         CREATE TABLE IF NOT EXISTS vacancies (
                             id SERIAL PRIMARY KEY
                             , url TEXT NOT NULL
                             , title TEXT NOT NULL
                             , added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                             , UNIQUE(url, title)
                         )
                         """)

        self.conn.commit()

    def process_item(self, item, spider):
        # Спробуємо вставити. Якщо така пара url+title є — нічого не робимо.
        self.cur.execute("""
                         INSERT INTO vacancies (url, title)
                         VALUES (%s, %s) ON CONFLICT (url, title) DO NOTHING
                         """, (item['url'], item['title']))

        self.conn.commit()

        # Якщо rowcount == 1, значить рядок був реально доданий (він новий)
        if self.cur.rowcount == 1:
            item['is_new'] = True
            return item
        else:
            raise DropItem(f"URL+Title already exists in db: {item}")

    def close_spider(self, spider):
        # Закриваємо курсор, тільки якщо він взагалі був створений
        if hasattr(self, 'cur') and self.cur:
            try:
                self.cur.close()
            except Exception:
                pass

        # Закриваємо конект, якщо він існує
        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.close()
            except Exception:
                pass





class TelegramPipeline:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    @classmethod
    def from_crawler(cls, crawler):
        # Витягуємо налаштування з settings.py
        token = crawler.settings.get('TELEGRAM_TOKEN')
        chat_id = crawler.settings.get('TELEGRAM_CHAT_ID')

        if not token or not chat_id:
            raise NotConfigured("Telegram Token or Chat ID not found!")

        return cls(token, chat_id)

    def process_item(self, item, spider):
        # Відправляємо повідомлення
        message = f"🌟 *Нова вакансія!*\n\n" \
                  f"📋 *Назва:* {item['title']}\n" \
                  f"🔗 [Переглянути]({item['url']})"

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"  # Щоб посилання було красивим
        }

        try:
            response = requests.post(self.api_url, data=payload)
            response.raise_for_status()
        except Exception as e:
            spider.logger.error(f"Telegram error: {e}")

        return item