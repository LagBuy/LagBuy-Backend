import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from apps.userauth.permissions import IsSeller
from common.utils.responses import error_response, success_response

from .models import Category, Product
from .serializers import (
    CategorySerializer,
    InventoryUpdateSerializer,
    ProductSerializer,
)

logger = logging.getLogger(__name__)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            self.permission_classes = [IsAdminUser]
        return super().get_permissions()


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            self.permission_classes = [IsAuthenticated, IsSeller]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

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
