import logging
from rest_framework import status
from rest_framework import APIView

from .models import Riders
from .serializers import RidersSerializer
from common.utils.responses import success_response, error_response

logger = logging.getLogger(__name__)
