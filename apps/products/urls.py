from django.urls import path
from drf_spectacular.utils import extend_schema_view, extend_schema

from .views import CategoryViewSet, ProductViewSet, ImageUploadView, ViewedProductsViewSet

ProductViewSet = extend_schema_view(
    list=extend_schema(tags=["Products"], summary="List all products"),
    retrieve=extend_schema(tags=["Products"], summary="Retrieve a product by ID"),
    create=extend_schema(tags=["Products"], summary="Create a new product"),
    partial_update=extend_schema(tags=["Products"], summary="Partially update a product"),
    destroy=extend_schema(tags=["Products"], summary="Delete a product"),
    update_stock=extend_schema(tags=["Products"], summary="Update product stock"),
)(ProductViewSet)

CategoryViewSet = extend_schema_view(
    list=extend_schema(tags=["Categories"], summary="List all categories"),
    create=extend_schema(tags=["Categories"], summary="Create a new category"),
    update=extend_schema(tags=["Categories"], summary="Update a category"),
    destroy=extend_schema(tags=["Categories"], summary="Delete a category"),
)(CategoryViewSet)

ImageUploadView = extend_schema_view(
    post=extend_schema(tags=["Products"], summary="Upload an image"),
)(ImageUploadView)

ViewedProductsViewSet = extend_schema_view(
    list=extend_schema(tags=["Products"], summary="List viewed products"),
)(ViewedProductsViewSet)

category_list = CategoryViewSet.as_view({"get": "list", "post": "create"})

category_detail = CategoryViewSet.as_view({"put": "update", "delete": "destroy"})

product_list = ProductViewSet.as_view({"get": "list", "post": "create"})

product_detail = ProductViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

product_update_stock = ProductViewSet.as_view({"post": "update_stock"})

viewed_products_list = ViewedProductsViewSet.as_view({"get": "list"})

urlpatterns = [
    path("categories/", category_list, name="category-list"),
    path("categories/<uuid:pk>/", category_detail, name="category-detail"),
    path("", product_list, name="product-list"),
    path("<uuid:pk>/", product_detail, name="product-detail"),
    path(
        "<uuid:pk>/update-stock/",
        product_update_stock,
        name="product-update-stock",
    ),
    path("upload-image/", ImageUploadView.as_view(), name="image-upload"),
    path("viewed/", viewed_products_list, name="viewed-products-list"),
]
