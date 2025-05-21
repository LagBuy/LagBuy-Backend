from django.urls import path

from .views import CartItemViewSet, CartViewSet

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
