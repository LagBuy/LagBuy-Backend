import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils.responses import error_response, success_response

from .models import Order
from .permissions import IsSeller
from .serializers import (OrderSerializer, OrderStatusUpdateSerializer,
                          SellerOrderSerializer)

logger = logging.getLogger(__name__)


class OrderCreateView(APIView):
    """Order create view class"""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """Method to create an order"""
        try:
            serializer = OrderSerializer(
                data=request.data, context={"request": request}
            )
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    message="Order created successfully.",
                    data=serializer.data,
                    status_code=status.HTTP_201_CREATED,
                )
            return error_response(
                message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return error_response(
                message="An error occurred while creating the order.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OrderDetailView(APIView):
    """Order detail view class"""

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id, *args, **kwargs):
        """Method to retrieve an order"""
        try:
            order = Order.objects.get(id=order_id)
            serializer = OrderSerializer(order)
            return success_response(
                message="Order retrieved successfully.", data=serializer.data
            )
        except Order.DoesNotExist:
            return error_response(
                message="Order not found.", status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving order: {e}")
            return error_response(
                message="An error occurred while retrieving the order.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OrderStatusUpdateView(APIView):
    """Order status update view class"""

    permission_classes = [IsAdminUser]

    def put(self, request, order_id, *args, **kwargs):
        """Method to update an order status"""
        try:
            order = Order.objects.get(id=order_id)
            serializer = OrderStatusUpdateSerializer(
                order, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    message="Order status updated successfully.", data=serializer.data
                )
            return error_response(
                message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Order.DoesNotExist:
            return error_response(
                message="Order not found.", status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return error_response(
                message="An error occurred while updating the order status.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SellerOrderListView(APIView):
    """View to retrieve orders for the seller's products"""

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request, *args, **kwargs):
        """Method to retrieve orders for the seller's products"""
        try:
            seller = request.user
            orders = Order.objects.filter(items__product__seller=seller).distinct()
            serializer = SellerOrderSerializer(
                orders, many=True, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving seller orders: {e}")
            return error_response(
                message="An error occurred while retrieving the orders.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
