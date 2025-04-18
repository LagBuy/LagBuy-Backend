from rest_framework import serializers
from .models import Coupon
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.products.models import Product


class CouponSerializer(serializers.ModelSerializer):
    """Serializer class for the Coupon model"""

    # seller = serializers.SlugRelatedField(slug_field='username', queryset=get_user_model().objects.all())
    # products = serializers.HyperlinkedRelatedField(view_name='products-by-id', lookup_field='id', many=True, read_only=False, queryset=Product.objects.all())
    # url = serializers.HyperlinkedIdentityField(view_name='coupon-detail', lookup_field='code', read_only=True)
    status = serializers.ReadOnlyField()

    class Meta:
        model = Coupon
        fields = [
            #"url",
            "id",
            "code",
            "discount_type",
            "discount_value",
            "min_purchase_quantity",
            "max_purchase_quantity",
            "valid_from",
            "valid_to",
            "usage_limit",
            "used_count",
            "status",
            "created_at",
            "updated_at",
            "seller",
            "products",
        ]
        read_only_fields = ["id", "used_count", "created_at", "updated_at"]

    def validate(self, data):
        """Validate the coupon data"""
        if data.get("valid_from", None) is not None and data.get("valid_to", None) is not None and data["valid_to"] < data["valid_from"]:
            raise serializers.ValidationError("'Valid to' has to be a later date than 'valid from'")
        if data.get("valid_to", None) is not None and data["valid_to"] <= timezone.now():
            raise serializers.ValidationError("Invalid Expiration date. Make sure you choose a future date and time")
        
        """The logged in user must be the owner/seller of the product(s) for them to create a valid coupon"""
        for product in data.get("products", []):
            if data["seller"] != product.seller:
                raise serializers.ValidationError("User must be the seller of the product")
        return data

class CouponBuyerSerializer(serializers.ModelSerializer):
    """A serializer to give the buyers only a minimal view of the coupon details"""
    status = serializers.ReadOnlyField()
    class Meta:
        model = Coupon
        fields = [
            #"url",
            "id",
            "code",
            "discount_type",
            "discount_value",
            "status"
        ]
        read_only_fields = ["id", "code", "discount_type", "discount_value"]
