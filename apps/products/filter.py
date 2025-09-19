from django_filters import rest_framework as filters
from .models import Product, Category

class ProductFilter(filters.FilterSet):
    """A filter set class for the product view"""
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    vendor = filters.CharFilter(field_name="seller__vendor_profile__business_name", lookup_expr="iexact")
    city = filters.CharFilter(field_name="seller__vendor_profile__business_location_city", lookup_expr="icontains")
    state = filters.CharFilter(field_name="seller__vendor_profile__business_location_state", lookup_expr="icontains")
    categories = filters.ModelMultipleChoiceFilter(field_name="categories__name", to_field_name="name", queryset=Category.objects.all())
    # categories = filters.MultipleChoiceFilter(field_name="categories__name", choices=[(cat.name, cat.name) for cat in Category.objects.all()], conjoined=False)

    class Meta:
        model = Product
        fields = ["categories", "verified", "vendor", "city", "state", "min_price", "max_price"]
