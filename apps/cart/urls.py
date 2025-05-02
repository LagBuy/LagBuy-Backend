from django.urls import path

from .views import CartItemViewSet, CartViewSet

cart_list = CartViewSet.as_view({"get": "list", "delete": "destroy"})
cartitem_list = CartItemViewSet.as_view({"get": "list", "post": "create"})
cartitem_detail = CartItemViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

urlpatterns = [
    path("", cart_list, name="cart-list"),
    path("items/", cartitem_list, name="cartitem-list"),
    path("items/<int:pk>/", cartitem_detail, name="cartitem-detail"),
]
