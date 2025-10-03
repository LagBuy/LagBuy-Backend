from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.userAuth.models import CustomUser
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model."""

    total_price = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "coupon", "total_price"]


def group_item_by_vendor(items):
    """group the items by vendor"""
    grouped_items = {}
    for item in items:
        vendor = str(item.product.seller.id)
        if vendor not in grouped_items:
            grouped_items[vendor] = []
        grouped_items[vendor].append(OrderItemSerializer(item).data)
    return grouped_items


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model."""

    # items = OrderItemSerializer(many=True, required=False)
    vendor = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=CustomUser.objects.filter(roles__name="vendor")
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "buyer",
            "vendor",
            # "items",
            "payment_status",
            "delivery_address",
            "delivery_status",
            "service_charge",
            "created_at",
            "updated_at",
            "total_price",
            "delivery_fee",
        ]
        read_only_fields = [
            # "items",
            "created_at",
            "updated_at",
            "total_price",
            "delivery_fee",
            "service_charge",
            "delivery_status",
            "payment_status",
            "buyer",
        ]

    def validate(self, data):
        """Validate the order data."""
        if self.instance is None:
            """Ensure user has at least one of the vendor's product in his cart"""
            buyer = self.context["request"].user
            vendor = data.get("vendor")
            if not buyer.cart.items.filter(product__seller=vendor).exists():
                raise serializers.ValidationError(
                    "Your cart does not contain any products from this vendor."
                )
        return data

    @transaction.atomic
    def create(self, validated_data):
        """get items from user's cart and create order and order items."""
        buyer = self.context["request"].user
        vendor = validated_data.pop("vendor")
        cart = buyer.cart

        order = Order.objects.create(buyer=buyer, **validated_data)
        for cart_item in cart.items.filter(product__seller=vendor):
            product = cart_item.product
            if product.stock_quantity < cart_item.quantity:
                raise serializers.ValidationError(
                    f"Insufficient stock for product {product.name}"
                )
            product.stock_quantity -= cart_item.quantity
            product.save()
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=cart_item.quantity,
                coupon=getattr(cart_item, "coupon", None),
            )
        # TODO: Clear only the items from this vendor
        # cart.items.filter(product__seller=vendor).delete()
        # clear when the order has been paid for (payment successful)
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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Group items by seller
        grouped_items = group_item_by_vendor(
            instance.items.select_related("product__seller").all()
        )
        ret["items"] = grouped_items
        return ret


class OrderItemStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order item status."""

    class Meta:
        model = OrderItem
        fields = ["delivery_status"]

    def validate_delivery_status(self, value):
        # value is the desired new status string (e.g, "SHIPPED")
        item = self.instance
        allowed, reason = item.can_transition_delivery(value)
        if not allowed:
            raise serializers.ValidationError(reason)
        return value


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
