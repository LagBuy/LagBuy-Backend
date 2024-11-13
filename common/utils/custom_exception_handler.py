from rest_framework.views import exception_handler
from rest_framework import status
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    """Call the default DRF exception handler to
    get the standard error response"""
    response = exception_handler(exc, context)

    """Check if the exception is an
    Authentication error (e.g., 401 Unauthorized)"""
    if response is not None and response.status_code == status.HTTP_401_UNAUTHORIZED:
        return Response({
            "status": status.HTTP_401_UNAUTHORIZED,
            "message": "Authentication credentials were not provided."
        }, status=status.HTTP_401_UNAUTHORIZED)

    """Return the default response if
    it's not a 401 Unauthorized error"""
    return response
