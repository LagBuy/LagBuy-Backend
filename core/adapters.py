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
    
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """
        Override to ensure HTML email is sent on both signup and resend.
        """
        ctx = {
            "user": emailconfirmation.email_address.user,
            "activation_url": self.get_email_confirmation_url(request, emailconfirmation),
            "key": emailconfirmation.key,
            'site_name': settings.SITE_NAME,
        }

        subject = render_to_string("account/email/email_confirmation_subject.txt", ctx)
        subject = "".join(subject.splitlines())
        from_email = self.get_from_email()
        to = [emailconfirmation.email_address.email]

        # Render both text and HTML templates
        text_body = render_to_string("account/email/email_confirmation_message.txt", ctx)
        html_body = render_to_string("account/email/email_confirmation_message.html", ctx)

        msg = EmailMultiAlternatives(subject, text_body, from_email, to)
        msg.attach_alternative(html_body, "text/html")
        msg.send()
