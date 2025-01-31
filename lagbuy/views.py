from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils.responses import error_response, success_response

class APIStatusView(APIView):
    def get(self, request):
        return success_response({'active': True}, "Welcome to LagBuy API. Go to /api/schema/swagger to view all available endpoints")