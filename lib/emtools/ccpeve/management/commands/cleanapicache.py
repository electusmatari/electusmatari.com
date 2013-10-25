import datetime

from django.core.management.base import BaseCommand
import django.db

from emtools.ccpeve.models import Cache


class Command(BaseCommand):
    def handle(self, *args, **options):
        Cache.objects.filter(cacheduntil__lt=datetime.datetime.utcnow()
                             ).delete()
        django.db.close_connection()
