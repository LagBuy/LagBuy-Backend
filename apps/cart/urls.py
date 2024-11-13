from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CartItemViewSet, CartViewSet

router = DefaultRouter()
router.register(r"carts", CartViewSet, basename="cart")
router.register(r"cart-items", CartItemViewSet, basename="cartitem")

urlpatterns = [
    path("", include(router.urls)),
]
