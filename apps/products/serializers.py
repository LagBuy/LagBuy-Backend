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

    seller = serializers.SerializerMethodField()
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
    vendor_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "seller",
            "vendor_id",
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

    def get_vendor_id(self, obj):
        return str(obj.seller.id) if obj.seller else None


class MinimalProductSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Product model.
    Includes only essential fields for cart display, including seller and first image.
    """

    seller = serializers.StringRelatedField()
    image = serializers.SerializerMethodField()
    vendor_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "price", "seller", "image", "vendor_id"]
        read_only_fields = ["id", "name", "price", "seller", "image", "vendor_id"]

    def get_image(self, obj):
        image = obj.images.first()
        return image.image_url if image else None

    def get_vendor_id(self, obj):
        return str(obj.seller.id) if obj.seller else None

    def get_seller(self, obj):
        """Return seller's store/business name if available, else fall back to user's email."""
        seller = obj.seller
        if not seller:
            return None
        # Prefer vendor profile business name when present
        vendor_profile = getattr(seller, "vendor_profile", None)
        if vendor_profile and vendor_profile.business_name:
            return vendor_profile.business_name
        # Fallback to string representation (email/username)
        return str(seller)
