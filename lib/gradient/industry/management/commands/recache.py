from django.core.management.base import BaseCommand

from gradient.industry.utils import redo_cache

class Command(BaseCommand):
    def handle(self, *args, **options):
        redo_cache()
