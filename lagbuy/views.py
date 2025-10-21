import os
from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from common.utils.responses import success_response, error_response


class APIStatusView(APIView):
    def get(self, request):
        return success_response({'active': True}, "Welcome to LagBuy API. Go to /api/schema/swagger to view all available endpoints")


class ServerLogsView(APIView):
    """
    View to retrieve server logs from debug.log file as plain text.
    Only accessible by admin users (is_staff=True).
    
    Query Parameters:
    - lines: Number of lines to retrieve from the end of the file (default: 100)
    - search: Search term to filter log entries (optional)
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            # Get query parameters
            num_lines = request.query_params.get('lines', 100)
            search_term = request.query_params.get('search', None)
            
            try:
                num_lines = int(num_lines)
                if num_lines <= 0:
                    return HttpResponse(
                        "Error: The 'lines' parameter must be a positive integer.",
                        content_type='text/plain',
                        status=400
                    )
            except ValueError:
                return HttpResponse(
                    "Error: The 'lines' parameter must be a valid integer.",
                    content_type='text/plain',
                    status=400
                )

            # Get the log file path
            log_file_path = os.path.join(settings.BASE_DIR, 'debug.log')

            # Check if the log file exists
            if not os.path.exists(log_file_path):
                return HttpResponse(
                    "Error: Log file not found.",
                    content_type='text/plain',
                    status=404
                )

            # Read the log file
            with open(log_file_path, 'r', encoding='utf-8', errors='replace') as log_file:
                # Read all lines
                all_lines = log_file.readlines()

            # Filter by search term if provided
            if search_term:
                filtered_lines = [line for line in all_lines if search_term.lower() in line.lower()]
                log_lines = filtered_lines[-num_lines:]
            else:
                log_lines = all_lines[-num_lines:]

            # Return logs as plain text
            log_content = ''.join(log_lines)
            
            return HttpResponse(
                log_content,
                content_type='text/plain',
                status=200
            )

        except PermissionError:
            return HttpResponse(
                "Error: Permission denied to read the log file.",
                content_type='text/plain',
                status=403
            )
        except Exception as e:
            return HttpResponse(
                f"Error: An error occurred while reading the log file: {str(e)}",
                content_type='text/plain',
                status=500
            )
