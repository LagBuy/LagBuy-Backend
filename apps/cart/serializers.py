from rest_framework import serializers
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = [
            "id",
            "user",
            "product",
            "quantity",
            "total_price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["total_price", "created_at", "updated_at"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = ["id", "user", "items", "total_price", "created_at", "updated_at"]
        read_only_fields = ["total_price", "created_at", "updated_at"]
