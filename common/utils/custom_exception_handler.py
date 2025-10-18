import logging

from django.core.mail import mail_admins
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .custom_exceptions import UserAlreadyExist
from .responses import customize_response
from .user_utils import send_user_exist_email

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Call the default DRF exception handler to
    get the standard error response"""
    response = exception_handler(exc, context)

    if isinstance(exc, UserAlreadyExist) and response is not None:
        """if user already exist return a success response and send user an email"""
        # Get email from request data
        request = context.get("request")
        user_email = None
        user_name = None

        if request and hasattr(request, "data"):
            user_email = request.data.get("email")
            # Try to get user name from the request data
            first_name = request.data.get("first_name", "")
            last_name = request.data.get("last_name", "")
            if first_name or last_name:
                user_name = f"{first_name} {last_name}".strip()

        # Send the user an email
        if user_email:
            try:
                send_user_exist_email(user_email, user_name)
                logger.info(f"User already exists email sent to {user_email}")
            except Exception as email_error:
                logger.error(
                    f"Failed to send user already exists email to {user_email}: {email_error}"
                )

        response.status_code = status.HTTP_201_CREATED
        return response

    """Check if the exception is an
    Authentication error (e.g., 401 Unauthorized)"""
    if response is not None:
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            return Response(
                {
                    "status": status.HTTP_401_UNAUTHORIZED,
                    "message": "Authentication credentials were not provided.",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        else:
            return response

    """internal server error"""
    request = context.get("request")
    # Build a safe error message without nested quotes inside f-strings
    error_message = (
        "\n\t\t\tINTERNAL SERVER ERROR:\n"
        + "=" * 80
        + "\n"
        + str(exc)
        + "\n"
        + "=" * 80
        + "\n"
        + f"In View\t\t: {context.get('view')}\n"
        + f"Logged in user\t: {request.user} [{getattr(request.user, 'email', 'Anonymous') if request else 'Anonymous'}]\n"
        + f"Accessing endpoint: {getattr(request, 'path', 'N/A')} ({getattr(getattr(request, 'resolver_match', None), 'url_name', 'N/A')})\n"
        + f"Method\t\t: {getattr(request, 'method', 'N/A')}\n"
        + f"Payload\t\t: {getattr(request, 'data', None)}\n"
        + "=" * 80
    )

    logger.error(error_message, exc_info=exc)

    # Send admin an email of the incident
    try:
        email_subject = f"Internal Server Error - {request.path}"
        email_message = (
            f"An internal server error occurred:\n\n"
            f"Exception: {exc}\n"
            f"View: {context.get('view')}\n"
            f"User: {request.user} [{request.user.email if hasattr(request.user, 'email') else 'Anonymous'}]\n"
            f"Endpoint: {request.path} ({request.resolver_match.url_name if request.resolver_match else 'N/A'})\n"
            f"Method: {request.method}\n"
            f"Payload: {request.data}\n\n"
            f"Check the logs for full traceback."
        )
        mail_admins(
            subject=email_subject,
            message=email_message,
            fail_silently=True,  # Don't raise exceptions if email fails
        )
    except Exception as email_error:
        logger.error(f"Failed to send admin email: {email_error}")

    return response
