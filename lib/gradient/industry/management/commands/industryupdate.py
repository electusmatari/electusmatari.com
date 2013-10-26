import logging

from django.core.management.base import BaseCommand

from gradient.industry.utils import update
import django.db


class Command(BaseCommand):
    def handle(self, *args, **options):
        logging.basicConfig()
        update()
        django.db.close_connection()
