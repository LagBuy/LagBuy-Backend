from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


# TODO: remove `cart`, `orders`, and `reviews` field from serializer
# TODO: The category field should return the categories names and not the ID. Edit it to reflect this
class ProductSerializer(serializers.ModelSerializer):
    seller = serializers.StringRelatedField()
    categories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all()
    )
    carts = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    orders = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    reviews = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "seller",
            "name",
            "description",
            "price",
            "images",
            "verified",
            "stock_quantity",
            "created_at",
            "updated_at",
            "categories",
            "carts",
            "orders",
            "reviews",
        ]
        read_only_fields = ["id", "seller", "created_at", "updated_at"]


class InventoryUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField()
