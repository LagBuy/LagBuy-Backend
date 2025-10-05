from rest_framework import serializers

from apps.products.serializers import MinimalProductSerializer

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer for CartItem model.
    Handles serialization of product, quantity, and computed total price.
    """

    total_price = serializers.ReadOnlyField()
    vendor_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id",
            "cart",
            "product",
            "quantity",
            "vendor_id",
            "total_price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["total_price", "created_at", "updated_at"]

    def to_representation(self, instance):
        # Use MinimalProductSerializer for reading
        ret = super().to_representation(instance)
        ret["product"] = MinimalProductSerializer(instance.product).data
        # include vendor id for convenience
        # the SerializerMethodField will also call `get_vendor_id`
        ret["vendor_id"] = (
            str(instance.product.seller.id)
            if instance.product and instance.product.seller
            else None
        )
        return ret

    def get_vendor_id(self, obj):
        return (
            str(obj.product.seller.id) if obj.product and obj.product.seller else None
        )

    def to_internal_value(self, data):
        # Accept product as an ID for writing
        if "product" in data and isinstance(data["product"], dict):
            data = data.copy()
            data["product"] = data["product"].get("id")
        return super().to_internal_value(data)


def group_item_by_vendor(items):
    """group the items by vendor"""
    grouped_items = {}
    for item in items:
        vendor = str(item.product.seller.id)
        if vendor not in grouped_items:
            grouped_items[vendor] = []
        grouped_items[vendor].append(CartItemSerializer(item).data)
    return grouped_items


class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for Cart model.
    Includes nested cart items and computed total price.
    """

    # items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "user",
            # "items",
            "total_price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["total_price", "created_at", "updated_at"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Group items by vendor
        grouped_items = group_item_by_vendor(
            instance.items.select_related("product__seller").all()
        )
        ret["items"] = grouped_items
        return ret
