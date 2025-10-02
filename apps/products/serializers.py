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
    shop_location = serializers.SerializerMethodField()

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
            "shop_location",
            "created_at",
            "updated_at",
            "categories",
        ]
        read_only_fields = ["id", "verified", "seller", "created_at", "updated_at"]

    def validate_stock_quantity(self, value):
        """
        Ensure stock quantity is a non-negative integer.
        """
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative.")
        return value

    def get_shop_location(self, obj):
        """get vendor shop location"""
        return (
            obj.seller.vendor_profile.short_address
            if hasattr(obj.seller, "vendor_profile")
            else None
        )


class MinimalProductSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Product model.
    Includes only essential fields for cart display, including seller and first image.
    """

    seller = serializers.StringRelatedField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "price", "seller", "image"]
        read_only_fields = ["id", "name", "price", "seller", "image"]

    def get_image(self, obj):
        image = obj.images.first()
        return image.image_url if image else None
