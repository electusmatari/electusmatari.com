from django.core.management.base import BaseCommand

from emtools.emauth import userauth
import django.db


class Command(BaseCommand):
    def handle(self, *args, **options):
        userauth.authenticate_users()
        django.db.close_connection()
