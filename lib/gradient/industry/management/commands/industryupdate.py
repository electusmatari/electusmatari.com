import logging

from django.core.management.base import BaseCommand

from gradient.industry.utils import update

class Command(BaseCommand):
    def handle(self, *args, **options):
        logging.basicConfig()
        update()
