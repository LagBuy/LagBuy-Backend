from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives


class CustomAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        """
        Returns the URL for email confirmation.
        Points to the frontend URL for better UX.
        """
        key = emailconfirmation.key
        return f"{settings.FRONTEND_URL}verify-email/{key}/"
