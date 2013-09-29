import datetime

from django.core.management.base import BaseCommand

from emtools.ccpeve.models import Cache

class Command(BaseCommand):
    def handle(self, *args, **options):
        Cache.objects.filter(cacheduntil__lt=datetime.datetime.utcnow()
                             ).delete()
