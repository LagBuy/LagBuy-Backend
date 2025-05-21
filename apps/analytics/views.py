import logging

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from common.utils.responses import success_response, error_response
from apps.orders.models import OrderItem, Order
from apps.userauth.permissions import IsOwnerSeller


logger = logging.getLogger(__name__)

class TotalSale(APIView):
    """Get total sales of the seller"""
    permission_classes = [IsAuthenticated, IsOwnerSeller]

    def get(self, request, *args, **kwargs):
        """get total sales"""

        # TODO: Test to ensure only a seller can access this.
        orderItems = OrderItem.objects.filter(
            order__payment_status=Order.PaymentStatus.PAID,
            product__seller = request.user)

        total_prices = sum([i.total_price for i in orderItems])

        return success_response(
            message="Total sales",
            data = {"total sale": total_prices}
        )

