import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from apps.userauth.permissions import IsASeller, IsOwnerSeller
from common.utils.responses import error_response, success_response

from .filter import ProductFilter
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer

logger = logging.getLogger(__name__)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Viewset for managing product categories.
    Only admins can create, update, or delete categories.
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            self.permission_classes = [IsAdminUser]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return success_response(
                serializer.data, "Categories retrieved successfully."
            )
        except Exception as e:
            logger.error(f"Error retrieving categories: {e}")
            return error_response(
                "An error occurred while retrieving categories.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return success_response(serializer.data, "Category retrieved successfully.")
        except Exception as e:
            logger.error(f"Error retrieving category: {e}")
            return error_response(
                "An error occurred while retrieving the category.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    serializer.data,
                    "Category created successfully.",
                    status.HTTP_201_CREATED,
                )
            return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return error_response(
                "An error occurred while creating the category.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    serializer.data, "Category updated successfully."
                )
            return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating category: {e}")
            return error_response(
                "An error occurred while updating the category.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return success_response(
                {}, "Category deleted successfully.", status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            return error_response(
                "An error occurred while deleting the category.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProductViewSet(viewsets.ModelViewSet):
    """
    Viewset for managing products.
    Sellers can create, update, and delete their products.
    All users can view products.
    """

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ["name", "description", "categories__name"]
    http_method_names = ["get", "post", "put", "patch", "delete"]
    filterset_class = ProductFilter

    def get_permissions(self):
        action_permissions = {
            "create": [IsAuthenticated, IsASeller],
            "update": [IsAuthenticated, IsOwnerSeller],
            "partial_update": [IsAuthenticated, IsOwnerSeller],
            "destroy": [IsAuthenticated, IsOwnerSeller],
        }
        self.permission_classes = action_permissions.get(
            self.action, self.permission_classes
        )
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return success_response(serializer.data, "Products retrieved successfully.")
        except Exception as e:
            logger.error(f"Error retrieving products: {e}")
            return error_response(
                "An error occurred while retrieving products.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return success_response(serializer.data, "Product retrieved successfully.")
        except Exception as e:
            logger.error(f"Error retrieving product: {e}")
            return error_response(
                "An error occurred while retrieving the product.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save(seller=request.user)
                return success_response(
                    serializer.data,
                    "Product created successfully.",
                    status.HTTP_201_CREATED,
                )
            return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            return error_response(
                "An error occurred while creating the product.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    serializer.data, "Product updated successfully."
                )
            return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            logger.warning(str(e))
            return error_response(str(e), status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Error updating product: {e}")
            return error_response(
                "An error occurred while updating the product.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    serializer.data, "Product updated successfully."
                )
            return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            logger.warning(str(e))
            return error_response(str(e), status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Error updating product: {e}")
            return error_response(
                "An error occurred while updating the product.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return success_response(
                {}, "Product deleted successfully.", status.HTTP_204_NO_CONTENT
            )
        except PermissionDenied as e:
            logger.warning(str(e))
            return error_response(str(e), status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return error_response(
                "An error occurred while deleting the product.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsOwnerSeller],
    )
    def update_stock(self, request, pk):
        """
        Custom action to update the stock quantity of a product.
        Only the seller/owner of the product can update its stock.
        """
        try:
            product = Product.objects.get(pk=pk)
            serializer = self.get_serializer(product, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    {"stock_quantity": serializer.data.get("stock_quantity")},
                    "Stock updated successfully",
                )
            return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            logger.warning(str(e))
            return error_response(str(e), status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Error updating stock: {e}")
            return error_response(
                "An error occurred while updating stock.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
