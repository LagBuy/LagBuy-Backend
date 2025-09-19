import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.views import APIView

from common.utils.responses import error_response, success_response
from apps.userAuth.permissions import IsASeller

from .models import Order, OrderItem
from .serializers import (
    OrderSerializer,
    OrderItemStatusUpdateSerializer,
    SellerOrderItemSerializer,
)

logger = logging.getLogger(__name__)


class OrderListCreateView(APIView):
    """
    API view for listing and creating orders.
    Only authenticated users can access their orders or create new ones.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post"]

    def get(self, request, *args, **kwargs):
        """List all orders for the authenticated user."""
        try:
            orders = Order.objects.filter(buyer=request.user)
            serializer = OrderSerializer(orders, many=True)
            return success_response(
                message="Orders retrieved successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error retrieving orders: {e}")
            return error_response(
                message="An error occurred while retrieving the orders.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request, *args, **kwargs):
        """Create a new order."""
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
    http_method_names = ["get", "patch", "delete"]

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


class OrderItemStatusUpdateView(APIView):
    """
    API view for updating the status of an order.
    Only admins can update order status.
    """

    permission_classes = [IsAdminUser]
    http_method_names = ["put"]

    def put(self, request, orderitem_id, *args, **kwargs):
        """Update the status of an order item."""
        try:
            order_item = OrderItem.objects.get(id=orderitem_id)
            serializer = OrderItemStatusUpdateSerializer(
                order_item, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    message="Order Item status updated successfully.", data=serializer.data
                )
            return error_response(
                message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except OrderItem.DoesNotExist:
            return error_response(
                message="Order Item not found.", status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating order item status: {e}")
            return error_response(
                message="An error occurred while updating the order item status.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SellerOrderListView(APIView):
    """
    API view to retrieve all orders that include products belonging to the seller.
    Only authenticated sellers can access this view.
    """

    permission_classes = [IsAuthenticated, IsASeller]
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        """Retrieve all orders for the authenticated seller."""
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
