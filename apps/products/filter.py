from django_filters import rest_framework as filters
from .models import Product

class ProductFilter(filters.FilterSet):
    """A filter set class for the product view"""
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Product
        fields = ["categories", "verified"]
