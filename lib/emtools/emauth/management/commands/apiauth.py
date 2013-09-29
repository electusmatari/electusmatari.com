from django.core.management.base import BaseCommand

from emtools.emauth import userauth

class Command(BaseCommand):
    def handle(self, *args, **options):
        userauth.authenticate_users()
