from rest_framework import serializers

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model."""

    total_price = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "coupon", "total_price"]


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model."""

    items = OrderItemSerializer(many=True)
    total_price = serializers.ReadOnlyField()
    delivery_fee = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            "id",
            "buyer",
            "seller",
            "items",
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
        if not data["items"]:
            raise serializers.ValidationError("Order must contain at least one item.")
        return data

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order status."""

    class Meta:
        model = Order
        fields = ["delivery_status", "payment_status"]
