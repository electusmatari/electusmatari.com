from django.core.management.base import BaseCommand

from emtools.intel.feedfetcher import fetch_all_feeds, clean_kills
import django.db


class Command(BaseCommand):
    def handle(self, *args, **options):
        fetch_all_feeds()
        clean_kills()
        django.db.close_connection()
