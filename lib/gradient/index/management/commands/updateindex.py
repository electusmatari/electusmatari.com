from django.core.management.base import BaseCommand

from gradient.index.utils import update_index

class Command(BaseCommand):
    def handle(self, *args, **options):
        update_index()
