from django.core.management.base import BaseCommand

from gradient.index.utils import update_index
import django.db


class Command(BaseCommand):
    def handle(self, *args, **options):
        update_index()
        django.db.close_connection()
