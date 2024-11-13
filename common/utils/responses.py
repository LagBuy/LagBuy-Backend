from rest_framework.response import Response
from rest_framework import status

def error_response(message, status_code):
    """Helper function to format error responses."""
    return Response({
        "status": status_code,
        "message": message
    }, status=status_code)

def success_response(data, message, status_code=status.HTTP_200_OK):
    """Helper function to format success responses."""
    return Response({
        "status": status_code,
        "message": message,
        "data": data
    }, status=status_code)
