from rest_framework import serializers

from apps.products.serializers import MinimalProductSerializer

from .models import Cart, CartItem


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

    def to_representation(self, instance):
        # Use MinimalProductSerializer for reading
        ret = super().to_representation(instance)
        ret["product"] = MinimalProductSerializer(instance.product).data
        return ret

    def to_internal_value(self, data):
        # Accept product as an ID for writing
        if "product" in data and isinstance(data["product"], dict):
            data = data.copy()
            data["product"] = data["product"].get("id")
        return super().to_internal_value(data)


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
