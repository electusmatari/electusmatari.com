from django.core.management.base import BaseCommand

from gradient.industry.utils import redo_cache
import django.db


class Command(BaseCommand):
    def handle(self, *args, **options):
        redo_cache()
        django.db.close_connection()
