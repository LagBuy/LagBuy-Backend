from django.urls import path

from .views import OrderViewSet

urlpatterns = [
    path(
        "",
        OrderViewSet.as_view({"get": "list", "post": "create"}),
        name="order_list",
    ),
    path(
        "<int:pk>/",
        OrderViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="order_detail",
    ),
]
