from rest_framework import serializers
from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model."""

    total_price = serializers.ReadOnlyField()
    delivery_fee = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            "id",
            "buyer",
            "seller",
            "products",
            "payment_status",
            "delivery_address",
            "delivery_status",
            "created_at",
            "updated_at",
            "total_price",
            "delivery_fee",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "delivery_status",
            "payment_status",
        ]

    def validate(self, data):
        """Validate the order data."""
        if data["buyer"] == data["seller"]:
            raise serializers.ValidationError(
                "Buyer and seller cannot be the same user."
            )
        if not data["products"]:
            raise serializers.ValidationError(
                "Order must contain at least one product."
            )
        return data


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order status."""

    class Meta:
        model = Order
        fields = ["delivery_status", "payment_status"]
