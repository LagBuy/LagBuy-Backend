import logging

from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.views import APIView

from apps.userAuth.permissions import IsARider
from apps.orders.models import OrderItem
from common.utils.responses import error_response, success_response

from .serializers import (RiderOrderItemSerializer,
                          UpdateOrderItemAssignedRidersSerializer,
                          AdminRiderOrderItemSerializer)

logger = logging.getLogger(__name__)


class GetAllAssignedOrderRequest(APIView):
    """Get order items that has been assigned to a rider
    for them to accept
    """
    permission_classes = [IsAuthenticated, IsARider]
    
    def get(self, request, *args, **kwargs):
        try:
            orders = OrderItem.objects.filter(
                delivery_status=OrderItem.DeliveryStatus.PENDING,
                assigned_riders=request.user,
                rider=None
                ).all()
            serializer = RiderOrderItemSerializer(orders, many=True)
            return success_response(serializer.data, "Items fetched successfully")
        except Exception as e:
            logger.error(f"Error while fetching rider's order items: {e}")
            return error_response("Internal server error while fetching items", status.HTTP_500_INTERNAL_SERVER_ERROR)


class AcceptOrDeclineOrderRequest(APIView):
    """View to allow a rider accept or decline an order"""
    permission_classes = [IsAuthenticated, IsARider]

    def put(self, request, item_id, *args, **kwargs):
        """update the rider assinged to an item"""
        try:
            accept = request.data.get("accept", None)
            if accept == None:
                return error_response(
                    "Missing required query parameter: `accept`, should be set to true or false",
                    status.HTTP_400_BAD_REQUEST
                )
            elif accept not in [True, False]:
                return error_response(
                    "Wrong query parameter: `accept`, should be set to true or false",
                    status.HTTP_400_BAD_REQUEST
                )
            orderItem = OrderItem.objects.get(id=item_id, rider=None)
            if accept:
                if request.user not in orderItem.assigned_riders.all():
                    return error_response(
                        "Item is not assinged to rider",
                        status.HTTP_400_BAD_REQUEST
                    )
                orderItem.rider = request.user
                orderItem.save()
                serializer = RiderOrderItemSerializer(orderItem)
                return success_response(serializer.data, "Item accepted successfully")
            else:
                orderItem.assigned_riders.remove(request.user)
                orderItem.save()
                return success_response({}, "Item declined successfully")
        except OrderItem.DoesNotExist:
            return error_response(
                message="Item not found or has been accepted by another rider",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error while updating rider accept status: {e}")
            return error_response(
                message="An error occured while updating accept status",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetUndeliveredOrderItems(APIView):
    """Get order items that has been assigned to a rider
    and has been accepted but not been delivered
    """
    permission_classes = [IsAuthenticated, IsARider]

    def get(self, request, *args, **kwargs):
        """Get order items to be delivered"""
        try:
            orders = OrderItem.objects.filter(rider=request.user, delivery_status=OrderItem.DeliveryStatus.PENDING).all()
            serializer = RiderOrderItemSerializer(orders, many=True)
            return success_response(serializer.data, "Items fetched successfully")
        except Exception as e:
            logger.error(f"Error while fetching rider's order items: {e}")
            return error_response("Internal server error while fetching items", status.HTTP_500_INTERNAL_SERVER_ERROR)


class RiderUpdateOrderItemPickUpStatus(APIView):
    """Update if the order has been picked up"""
    # TODO: add a view for a rider to update if they have picked up
    # an item. verify the logic, will the seller have to be involved
    # to confirm it has been picked up?
    pass


class GetDeliveredOrderItems(APIView):
    """Get delivered order items for a rider. Delivery history"""
    permission_classes = [IsAuthenticated, IsARider]

    def get(self, request, *args, **kwargs):
        """Get order items to be delivered"""
        try:
            orders = OrderItem.objects.filter(rider=request.user, delivery_status=OrderItem.DeliveryStatus.DELIVERED).all()
            serializer = RiderOrderItemSerializer(orders, many=True)
            return success_response(serializer.data, "Items fetched successfully")
        except Exception as e:
            logger.error(f"Error while fetching rider's order items: {e}")
            return error_response("Internal server error while fetching items", status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminListAllOrder(APIView):
    """Assign an order item to a rider. Admin only"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        """Admin view all orders."""
        try:
            orders = OrderItem.objects.filter(
                ready_for_pickup=True,
                delivery_status=OrderItem.DeliveryStatus.PENDING
                ).all()
            serializer = AdminRiderOrderItemSerializer(orders, many=True)
            return success_response(serializer.data, "Items fetched successfully")
        except Exception as e:
            logger.error(f"Error while fetching rider's order items: {e}")
            return error_response("Internal server error while fetching items", status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminAssignOrder(APIView):
    """Assign an order item to a rider. Admin only"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, item_id, *args, **kwargs):
        """Admin view all individual orders. TODO"""
        pass

    def put(self, request, item_id, *args, **kwargs):
        """Assign an order to a rider"""
        try:
            data = request.data
            if not data:
                return error_response("No data provided", status.HTTP_400_BAD_REQUEST)
            orderItem = OrderItem.objects.get(id=item_id)
            serializer = UpdateOrderItemAssignedRidersSerializer(orderItem, data=data)
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    data=serializer.data,
                    message="Rider assigned successfully",
                    status_code=status.HTTP_200_OK
                )
            return error_response(
                message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except OrderItem.DoesNotExist:
            return error_response("Invalid Item ID", status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Internal server error while assigning order to rider: {e}")
            return error_response("Internal server error while assigning order", status.HTTP_500_INTERNAL_SERVER_ERROR)

# TODO: ads a view to allow rider and buyer update the delivery status
# TODO: add a view to allow admin view each order for easy assigning
# TODO: add a view for admin to view all riders in the same location as the pickup
# TODO: add view in Order app to allow vendors update if an order is ready for pickup
# TODO: Analytics: total accepted order, total delivered, total assigned
# total kilometers covered, total money made. a `rider_delivery_commission`
# should be added to the order item table to track the delivery commission
# of each order (also a field to record the delivery km for each order item)


