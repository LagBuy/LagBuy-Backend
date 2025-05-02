from rest_framework import serializers
from .models import Cart, CartItem


# TODO: Use minimal product serializer when available
class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer for CartItem model.
    Handles serialization of product, quantity, and computed total price.
    """

    total_price = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "cart",
            "product",
            "quantity",
            "total_price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["total_price", "created_at", "updated_at"]


class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for Cart model.
    Includes nested cart items and computed total price.
    """

    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "user",
            "items",
            "total_price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["total_price", "created_at", "updated_at"]
