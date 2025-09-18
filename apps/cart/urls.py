from django.urls import path
from drf_spectacular.utils import extend_schema_view, extend_schema

from .views import CartItemViewSet, CartViewSet

CartViewSet = extend_schema_view(
    list=extend_schema(tags=["Cart"], summary="Retrieve the current user's cart"),
    destroy=extend_schema(tags=["Cart"], summary="Clear the current user's cart"),
    add_item=extend_schema(tags=["Cart"], summary="Add an item to the cart"),
    remove_item=extend_schema(tags=["Cart"], summary="Remove an item from the cart"),
)(CartViewSet)

CartItemViewSet = extend_schema_view(
    list=extend_schema(tags=["Cart"], summary="List all items in the current user's cart"),
    retrieve=extend_schema(tags=["Cart"], summary="Retrieve a cart item by ID"),
)(CartItemViewSet)

# Cart views
cart_list = CartViewSet.as_view({"get": "list", "delete": "destroy"})
add_cartitem = CartViewSet.as_view({"post": "add_item"})
remove_cartitem = CartViewSet.as_view({"delete": "remove_item"})

# Cart item views (read-only)
cartitem_list = CartItemViewSet.as_view({"get": "list"})
cartitem_detail = CartItemViewSet.as_view({"get": "retrieve"})

urlpatterns = [
    path("", cart_list, name="cart-list"),
    path("items/add/", add_cartitem, name="add-cartitem"),
    path("items/remove/", remove_cartitem, name="remove-cartitem"),
    path("items/", cartitem_list, name="cartitem-list"),
    path("items/<int:pk>/", cartitem_detail, name="cartitem-detail"),
]
