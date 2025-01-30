from django.core.management.base import BaseCommand
from apps.users.models import CustomUser
import os

email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin")
first_name = os.getenv("DJANGO_SUPERUSER_FIRST_NAME", "admin")
last_name =  os.getenv("DJANGO_SUPERUSER_LASTNAME", "admin")
phone_number = os.getenv("DJANGO_SUPERUSER_PHONE_NUMBER", "admin")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin")


class Command(BaseCommand):

    def handle(self, *args, **options):
        if not CustomUser.objects.filter(email=email).exists():
            CustomUser.objects.create_superuser(email, first_name, last_name, phone_number, password), 