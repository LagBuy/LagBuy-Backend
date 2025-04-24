import logging

from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.userauth.permissions import IsSeller
from common.utils.responses import error_response, success_response

from .models import Category, Product
from .serializers import (
    CategorySerializer,
    InventoryUpdateSerializer,
    ProductSerializer,
)
from .filter import ProductFilter

logger = logging.getLogger(__name__)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            self.permission_classes = [IsAdminUser]
        return super().get_permissions()

# TODO: use the custom Response handler for the project. (apply to other apps also)
# TODO: implement logging for all the views (apply to other apps also)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ["name", "description", "categories__name"]
    filterset_class = ProductFilter

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            self.permission_classes = [IsAuthenticated, IsSeller]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

    # TODO: use a partial update view instead
    # TODO: implement a method to remove 'user' field from a request data (apply to other apps also)
    # TODO: implement a custom `get_object()` function
    # TODO: ensure only the seller/owner of a product can update it's stock
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def update_stock(self, request, pk=None):
        try:
            product = self.get_object()
            serializer = InventoryUpdateSerializer(data=request.data)
            if serializer.is_valid():
                new_quantity = (
                    product.stock_quantity + serializer.validated_data["quantity"]
                )
                if new_quantity < 0:
                    return error_response(
                        "Insufficient stock.", status.HTTP_400_BAD_REQUEST
                    )
                product.stock_quantity = new_quantity
                product.save()
                return success_response(
                    {"stock_quantity": product.stock_quantity},
                    "Stock updated successfully",
                )
            return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating stock: {e}")
            return error_response(
                "An error occurred while updating stock.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
