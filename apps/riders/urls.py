from django.urls import path

from .views import (AdminAssignOrder,
                    AdminListAllOrder,
                    GetAllAssignedOrderRequest,
                    AcceptOrDeclineOrderRequest,
                    GetUndeliveredOrderItems,
                    GetDeliveredOrderItems)

urlpatterns = [
    path("items-assign/<uuid:order_id>/", AdminAssignOrder.as_view(), name="admin-item-assign"),
    path("items-assign/", AdminListAllOrder.as_view(), name="admin-list-all-items"),
    path("orders/accepted/", GetUndeliveredOrderItems.as_view(), name="get-all-undelivered-items"),
    path("orders/assigned/", GetAllAssignedOrderRequest.as_view(), name="get-all-assigned-order"),
    path("orders/accept/<uuid:order_id>", AcceptOrDeclineOrderRequest.as_view(), name="accept-or-decline-assigned-order"),
    path("orders/delivered/", GetDeliveredOrderItems.as_view(), name="get-all-delivered-items")
]
