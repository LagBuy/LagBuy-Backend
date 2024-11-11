from django.urls import path

from .views import OrderCreateView, OrderDetailView, OrderStatusUpdateView

urlpatterns = [
    path("", OrderCreateView.as_view(), name="orders"),
    path("<uuid:order_id>/", OrderDetailView.as_view(), name="order-by-id"),
    path(
        "<uuid:order_id>/status/", OrderStatusUpdateView.as_view(), name="update-order"
    ),
]
