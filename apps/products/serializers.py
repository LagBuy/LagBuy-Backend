from rest_framework import serializers

from .models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for product categories.
    """

    class Meta:
        model = Category
        fields = ["id", "name", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializer for ProductImage model.
    - Returns product as string.
    """

    product = serializers.StringRelatedField()

    class Meta:
        model = ProductImage
        fields = ["id", "product", "image_url", "created_at", "updated_at"]
        read_only_fields = ["id", "product", "created_at", "updated_at"]


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for Product model.
    - Returns seller as string.
    - Returns category names instead of IDs.
    """

    seller = serializers.StringRelatedField()
    categories = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=Category.objects.all()
    )
    images = serializers.SlugRelatedField(
        many=True,
        slug_field="image_url",
        queryset=ProductImage.objects.all(),
        required=False,
    )

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
        ]
        read_only_fields = ["id", "seller", "created_at", "updated_at"]

    def validate_stock_quantity(self, value):
        """
        Ensure stock quantity is a non-negative integer.
        """
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative.")
        return value
