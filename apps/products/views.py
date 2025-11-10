import logging

from django.http import Http404
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.userAuth.permissions import IsASeller, IsOwnerSeller
from common.services.storage import STORAGE
from common.utils.responses import customize_response, error_response, success_response

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

    def get_permissions(self):
        if self.action in ["create"]:
            self.permission_classes = [IsASeller]
        if self.action in ["update", "partial_update", "destroy"]:
            self.permission_classes = [IsAdminUser]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return customize_response(response, "Categories retrieved successfully.")

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return customize_response(response, "Category retrieved successfully.")

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return customize_response(response, "Category created successfully.")

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return customize_response(response, "Category updated successfully.")

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        return customize_response(response, "Category deleted successfully.")


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

    def get_queryset(self):
        """enable filtering by seller via query param"""
        seller_id = self.request.query_params.get("vendor_id")
        if seller_id:
            return self.queryset.filter(seller_id=seller_id)
        return self.queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return customize_response(response, "Products retrieved successfully.")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if request.user.is_authenticated:
            request.user.user_profile.viewed_products.add(instance)
        response = Response(serializer.data)
        return customize_response(response, "Product retrieved successfully.")

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return customize_response(response, "Product created successfully.")

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return customize_response(response, "Product updated successfully.")

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        return customize_response(response, "Product updated successfully.")

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        return customize_response(response, "Product deleted successfully.")

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
        except Product.DoesNotExist as e:
            raise Http404
        except PermissionDenied as e:
            logger.warning(str(e))
            return error_response(str(e), status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Error updating stock: {e}")
            return error_response(
                "An error occurred while updating stock.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ImageUploadView(APIView):
    """
    API endpoint for uploading product images.
    Handles file uploads and returns the image URL on success.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    def post(self, request, *args, **kwargs):
        try:
            uploaded_image = request.FILES.get("image")
            if not uploaded_image:
                return Response(
                    {"detail": "No image file provided."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate file size
            if uploaded_image.size > self.MAX_FILE_SIZE:
                max_size_mb = self.MAX_FILE_SIZE / (1024 * 1024)
                return Response(
                    {"detail": f"File size exceeds maximum limit of {max_size_mb}MB."},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

            file_url = STORAGE.upload_file(
                uploaded_image, uploaded_image.name, uploaded_image.content_type
            )
            if file_url:
                return Response({"url": file_url}, status=status.HTTP_201_CREATED)
            return Response(
                {"detail": "Failed to upload image."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            raise e  # allows for proper flagging and debugging


class ViewedProductsViewSet(viewsets.ReadOnlyModelViewSet):
    """A viewset to view user's recently viewed products"""

    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

    def get_queryset(self):
        user = self.request.user
        return (
            user.user_profile.viewed_products.all()
        )  # .select_related('seller', 'categories')

    def list(self, request, *args, **kwargs):
        """Get list of user's recently viewed products"""
        response = super().list(request, *args, **kwargs)
        return customize_response(
            response, "Recently viewed products retrieved successfully"
        )
