"""Urls for Products app"""
from django.urls import path, include

from .views import GetProduct, GetAllProducts

urlpatterns = [
    # path('', CreateProduct.as_view(), name='create-product'),
    path('', GetAllProducts.as_view(), name='products'),
    path('<uuid:id>', GetProduct.as_view(), name='products-by-id'),
    # path('<uuid:id>/update/', UpdateProduct.as_view(), name='update-product'),
    # path('<uuid:id>/delete/', DeleteProduct.as_view(), name='delete-product'),
]
