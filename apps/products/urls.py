from django.urls import path

from .views import CategoryViewSet, ImageUploadView, ProductViewSet

category_list = CategoryViewSet.as_view({"get": "list", "post": "create"})

category_detail = CategoryViewSet.as_view({"put": "update", "delete": "destroy"})

product_list = ProductViewSet.as_view({"get": "list", "post": "create"})

product_detail = ProductViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

product_update_stock = ProductViewSet.as_view({"post": "update_stock"})

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
]
