from django.urls import path
from drf_spectacular.utils import extend_schema_view, extend_schema

from .views import (
    OrderListCreateView,
    OrderDetailView,
    OrderItemStatusUpdateView,
    SellerOrderListView,
)

OrderListCreateView = extend_schema_view(
    get=extend_schema(tags=["Orders"], summary="List all orders"),
    post=extend_schema(tags=["Orders"], summary="Create a new order"),
)(OrderListCreateView)
OrderDetailView = extend_schema_view(
    get=extend_schema(tags=["Orders"], summary="Retrieve order details by order ID"),
    patch=extend_schema(tags=["Orders"], summary="Update an order by order ID"),
    delete=extend_schema(tags=["Orders"], summary="Delete an order by order ID"),
)(OrderDetailView)
OrderItemStatusUpdateView = extend_schema_view(
    put=extend_schema(tags=["Orders"], summary="Update the status of an order item"),
)(OrderItemStatusUpdateView)
SellerOrderListView = extend_schema_view(
    get=extend_schema(tags=["Orders"], summary="List all orders for the authenticated seller"),
)(SellerOrderListView)

urlpatterns = [
    path("", OrderListCreateView.as_view(), name="orders"),
    path("<uuid:order_id>/", OrderDetailView.as_view(), name="order-by-id"),
    path(
        "<uuid:orderitem_id>/status/", OrderItemStatusUpdateView.as_view(), name="update-orderitem-status"
    ),
    path("seller-orders/", SellerOrderListView.as_view(), name="seller-orders"),
]
