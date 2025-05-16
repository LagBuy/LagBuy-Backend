from django.urls import path

from .views import (
    OrderListCreateView,
    OrderDetailView,
    OrderStatusUpdateView,
    SellerOrderListView,
)

urlpatterns = [
    path("", OrderListCreateView.as_view(), name="orders"),
    path("<uuid:order_id>/", OrderDetailView.as_view(), name="order-by-id"),
    path(
        "<uuid:order_id>/status/", OrderStatusUpdateView.as_view(), name="update-order"
    ),
    path("seller-orders/", SellerOrderListView.as_view(), name="seller-orders"),
]
