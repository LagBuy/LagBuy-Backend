from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view

from .views import (AdminAssignOrder,
                    AdminListAllOrder,
                    GetAllAssignedOrderRequest,
                    AcceptOrDeclineOrderRequest,
                    GetUndeliveredOrderItems,
                    GetDeliveredOrderItems)

AdminAssignOrder = extend_schema_view(
    get=extend_schema(tags=["Riders Dashboard"], summary="Get an order item by ID (Admin only)"),
    put=extend_schema(tags=["Riders Dashboard"], summary="Assign an order item to a rider (Admin only)")
)(AdminAssignOrder)
AdminListAllOrder = extend_schema_view(
    get=extend_schema(tags=["Riders Dashboard"], summary="List all order items (Admin only)")
)(AdminListAllOrder)
GetAllAssignedOrderRequest = extend_schema_view(
    get=extend_schema(tags=["Riders Dashboard"], summary="Get all order requests that has been assigned to the rider (Rider only)")
)(GetAllAssignedOrderRequest)
AcceptOrDeclineOrderRequest = extend_schema_view(
    put=extend_schema(tags=["Riders Dashboard"], summary="Accept or decline an assigned order request (Rider only)")
)(AcceptOrDeclineOrderRequest)
GetUndeliveredOrderItems = extend_schema_view(
    get=extend_schema(tags=["Riders Dashboard"], summary="Get all undelivered order items that has been accepted (Rider only)")
)(GetUndeliveredOrderItems)
GetDeliveredOrderItems = extend_schema_view(
    get=extend_schema(tags=["Riders Dashboard"], summary="Get all delivered order items (Rider only)")
)(GetDeliveredOrderItems)


urlpatterns = [
    path("items-assign/<uuid:item_id>/", AdminAssignOrder.as_view(), name="admin-item-assign"),
    path("items-assign/", AdminListAllOrder.as_view(), name="admin-list-all-items"),
    path("items/accepted/", GetUndeliveredOrderItems.as_view(), name="get-all-undelivered-items"),
    path("items/assigned/", GetAllAssignedOrderRequest.as_view(), name="get-all-assigned-order"),
    path("items/accept/<uuid:item_id>/", AcceptOrDeclineOrderRequest.as_view(), name="accept-or-decline-assigned-order"),
    path("items/delivered/", GetDeliveredOrderItems.as_view(), name="get-all-delivered-items")
]
