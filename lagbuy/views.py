import os
from django.conf import settings
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
    View to retrieve server logs from debug.log file.
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
                    return error_response(
                        "The 'lines' parameter must be a positive integer.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return error_response(
                    "The 'lines' parameter must be a valid integer.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Get the log file path
            log_file_path = os.path.join(settings.BASE_DIR, 'debug.log')

            # Check if the log file exists
            if not os.path.exists(log_file_path):
                return error_response(
                    "Log file not found.",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Read the log file
            with open(log_file_path, 'r', encoding='utf-8', errors='replace') as log_file:
                # Read all lines
                all_lines = log_file.readlines()

            # Filter by search term if provided
            if search_term:
                filtered_lines = [line for line in all_lines if search_term.lower() in line.lower()]
                log_lines = filtered_lines[-num_lines:]
                total_lines = len(filtered_lines)
            else:
                log_lines = all_lines[-num_lines:]
                total_lines = len(all_lines)

            # Get file size
            file_size = os.path.getsize(log_file_path)
            file_size_mb = round(file_size / (1024 * 1024), 2)

            # Prepare response data
            response_data = {
                'logs': ''.join(log_lines),
                'metadata': {
                    'total_lines_in_file': total_lines,
                    'lines_returned': len(log_lines),
                    'file_size_mb': file_size_mb,
                    'file_path': log_file_path,
                    'search_term': search_term,
                }
            }

            return success_response(
                response_data,
                f"Successfully retrieved {len(log_lines)} log entries."
            )

        except PermissionError:
            return error_response(
                "Permission denied to read the log file.",
                status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return error_response(
                f"An error occurred while reading the log file: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
