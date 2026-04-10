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
