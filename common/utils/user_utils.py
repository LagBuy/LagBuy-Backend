"""
Utility functions for user-related operations
"""
import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)


def send_user_exist_email(user_email, user_name=None):
    """
    Send an email to a user who tried to register with an existing email address.
    
    Args:
        user_email (str): The email address of the existing user
        user_name (str, optional): The name of the user if available
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Prepare context for the email template
        context = {
            'user_email': user_email,
            'user_name': user_name or 'User',
            'site_name': 'LagBuy',
            'support_email': settings.SUPPORT_EMAIL,
            'login_url': settings.LOGIN_URL,
        }
        
        # Render HTML email template
        html_message = render_to_string('emails/user_already_exists.html', context)
        
        # Create plain text version by stripping HTML tags
        plain_message = strip_tags(html_message)
        
        # Also use the text template if available
        try:
            plain_message = render_to_string('emails/user_already_exists.txt', context)
        except Exception:
            # If text template doesn't exist, use stripped HTML
            pass
        
        # Email subject
        subject = f'[{context["site_name"]}] Account Already Exists'
        
        # Create email with both HTML and plain text versions
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email]
        )
        email.attach_alternative(html_message, "text/html")
        
        # Send the email
        email.send(fail_silently=False)
        
        logger.info(f"User already exists email sent successfully to {user_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send user already exists email to {user_email}: {str(e)}")
        return False
