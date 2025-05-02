import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.views import APIView

from common.utils.responses import error_response, success_response

from .models import Order, OrderItem
from .permissions import IsSeller
from .serializers import (
    OrderSerializer,
    OrderStatusUpdateSerializer,
    SellerOrderItemSerializer,
)

logger = logging.getLogger(__name__)


class OrderCreateView(APIView):
    """
    API view for creating a new order.
    Only authenticated users can create orders.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
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
    """
    API view for retrieving, updating, and deleting a specific order.
    Only authenticated users can access their orders.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id, *args, **kwargs):
        """Retrieve a specific order by ID."""
        try:
            order = Order.objects.get(id=order_id, buyer=request.user)
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

    def patch(self, request, order_id, *args, **kwargs):
        """Update an order (only allowed for the owner)."""
        try:
            order = Order.objects.get(id=order_id, buyer=request.user)
            serializer = OrderSerializer(
                order, data=request.data, partial=True, context={"request": request}
            )
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    message="Order updated successfully.", data=serializer.data
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
            logger.error(f"Error updating order: {e}")
            return error_response(
                message="An error occurred while updating the order.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, order_id, *args, **kwargs):
        """Delete an order (only allowed for the owner)."""
        try:
            order = Order.objects.get(id=order_id, buyer=request.user)
            order.delete()
            return success_response(
                message="Order deleted successfully.",
                data={},
                status_code=status.HTTP_204_NO_CONTENT,
            )
        except Order.DoesNotExist:
            return error_response(
                message="Order not found.", status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deleting order: {e}")
            return error_response(
                message="An error occurred while deleting the order.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OrderStatusUpdateView(APIView):
    """
    API view for updating the status of an order.
    Only admins can update order status.
    """

    permission_classes = [IsAdminUser]

    def put(self, request, order_id, *args, **kwargs):
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
    """
    API view to retrieve all orders that include products belonging to the seller.
    Only authenticated sellers can access this view.
    """

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request, *args, **kwargs):
        try:
            seller = request.user
            orders = OrderItem.objects.filter(product__seller=seller).distinct()
            serializer = SellerOrderItemSerializer(
                orders, many=True, context={"request": request}
            )
            return success_response(
                message="Seller orders retrieved successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error retrieving seller orders: {e}")
            return error_response(
                message="An error occurred while retrieving the orders.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
