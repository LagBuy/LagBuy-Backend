from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import Order, OrderItem

# TODO: change the order implementation.
# Orders will be placed per vendor

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model."""

    total_price = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "coupon", "total_price"]


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model."""

    items = OrderItemSerializer(many=True, required=False)

    class Meta:
        model = Order
        fields = [
            "id",
            "buyer",
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
            "total_price",
            "delivery_fee",
            "delivery_status",
            "payment_status",
            "buyer",
        ]

    def validate(self, data):
        """Validate the order data."""
        if self.instance is None and not data.get("items"):
            raise serializers.ValidationError("Order must contain at least one item.")
        return data

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items")
        buyer = self.context["request"].user
        order = Order.objects.create(buyer=buyer, **validated_data)
        # TODO: what happens if a product is added twice
        for item_data in items_data:
            product = item_data["product"]
            if product.stock_quantity < item_data["quantity"]:
                raise serializers.ValidationError(
                    f"Insufficient stock for product {product.name}"
                )
            product.stock_quantity -= item_data["quantity"]
            product.save()
            OrderItem.objects.create(order=order, **item_data)
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Update order fields and its items if provided.
        Only delivery_address can be updated by the user.
        Only allow update if the order is less than 24 hours old.
        TODO: This restriction may change in the future.
        """
        if (timezone.now() - instance.created_at).total_seconds() > 86400:
            raise serializers.ValidationError(
                "Order can only be updated within 24 hours of creation."
            )
        delivery_address = validated_data.get("delivery_address", None)
        if delivery_address is not None:
            instance.delivery_address = delivery_address
            instance.save(update_fields=["delivery_address", "updated_at"])
        return instance


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order status."""

    class Meta:
        model = Order
        fields = ["delivery_status", "payment_status"]


class SellerOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model for seller's view."""

    total_price = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "coupon", "total_price"]


class SellerOrderSerializer(serializers.ModelSerializer):
    """Serializer for seller's view of orders."""

    items = serializers.SerializerMethodField()
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            "id",
            "buyer",
            "items",
            "delivery_address",
            "delivery_status",
            "total_price",
        ]

    def get_items(self, obj):
        """Get items that belong to the seller."""
        seller = self.context["request"].user
        items = obj.items.filter(product__seller=seller)
        return SellerOrderItemSerializer(items, many=True).data
