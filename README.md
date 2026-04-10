1. Пропонована структура проєкту
junior_job_notifier/
├── backend/
│   ├── manage.py
│   ├── backend/              # Django settings
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── jobs/                 # основний додаток
│   │   ├── __init__.py
│   │   ├── models.py         # Vacancy, Company
│   │   ├── serializers.py    # якщо DRF
│   │   ├── views.py
│   │   ├── tasks.py          # APScheduler / Celery tasks
│   │   ├── scraper.py        # адаптери для сайтів
│   │   └── telegram_bot.py   # відправка сповіщень
├── requirements.txt
├── README.md
└── .env
2. Основні моделі (models.py)
from django.db import models

class Company(models.Model):
    name = models.CharField(max_length=100)
    website = models.URLField()
    jobs_url = models.URLField()  # де публікуються вакансії

class Vacancy(models.Model):
    title = models.CharField(max_length=200)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    url = models.URLField(unique=True)
    published_at = models.DateField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)  # чи відправлено сповіщення
3. Scraper (scraper.py)
Для кожної компанії пишемо адаптер:
import requests
from bs4 import BeautifulSoup
from .models import Vacancy, Company
from datetime import datetime

def fetch_jobs_for_company(company: Company):
    response = requests.get(company.jobs_url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Приклад для конкретного сайту
    for job in soup.select(".job-card"):
        url = job.select_one("a")["href"]
        title = job.select_one(".job-title").text.strip()
        date_str = job.select_one(".date").text.strip()
        published_at = datetime.strptime(date_str, "%d.%m.%Y").date()

        Vacancy.objects.get_or_create(
            url=url,
            defaults={"title": title, "company": company, "published_at": published_at}
        )
4. Планувальник (tasks.py)
APScheduler (для початку, Celery можна пізніше):
from apscheduler.schedulers.background import BackgroundScheduler
from .scraper import fetch_jobs_for_company
from .models import Company

scheduler = BackgroundScheduler()

def scrape_all_companies():
    for company in Company.objects.all():
        fetch_jobs_for_company(company)

scheduler.add_job(scrape_all_companies, "interval", hours=6)
scheduler.start()
5. Telegram сповіщення (telegram_bot.py)
import telegram
from .models import Vacancy
from django.conf import settings

bot = telegram.Bot(token=settings.TELEGRAM_TOKEN)

def notify_new_vacancies():
    for vac in Vacancy.objects.filter(notified=False):
        msg = f"{vac.title} at {vac.company.name}\n{vac.url}"
        bot.send_message(chat_id=settings.TELEGRAM_CHAT_ID, text=msg)
        vac.notified = True
        vac.save()
6. CLI / Management command
Django підтримує custom commands:
python manage.py scrape_jobs
python manage.py notify_vacancies
# jobs/management/commands/scrape_jobs.py
from django.core.management.base import BaseCommand
from jobs.tasks import scrape_all_companies

class Command(BaseCommand):
    help = "Scrape job vacancies"

    def handle(self, *args, **options):
        scrape_all_companies()
        self.stdout.write(self.style.SUCCESS("Scraping finished"))
7. Deployment (безкоштовно)
Render Free Tier або Railway Free Tier — підтримують Django + PostgreSQL.
Можна хостити Telegram бота на тому ж сервері.