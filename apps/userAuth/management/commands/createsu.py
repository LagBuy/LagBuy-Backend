from django.core.management.base import BaseCommand
from apps.userAuth.models import CustomUser
from apps.profiles.models import UsersProfile
import os

email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin")
first_name = os.getenv("DJANGO_SUPERUSER_FIRST_NAME", "admin")
last_name =  os.getenv("DJANGO_SUPERUSER_LASTNAME", "admin")
phone_number = os.getenv("DJANGO_SUPERUSER_PHONE_NUMBER", "admin")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin")


class Command(BaseCommand):

    def handle(self, *args, **options):
        if not CustomUser.objects.filter(email=email).exists():
            user = CustomUser.objects.create_superuser(email, password)
            UsersProfile.objects.create(
                user=user, first_name=first_name, last_name=last_name, phone_number=phone_number
            )