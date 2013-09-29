from django.core.management.base import BaseCommand

from emtools.intel.feedfetcher import fetch_all_feeds, clean_kills

class Command(BaseCommand):
    def handle(self, *args, **options):
        fetch_all_feeds()
        clean_kills()
