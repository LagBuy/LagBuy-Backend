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
    # Read-only representation of related images (list of URLs)
    images = serializers.SlugRelatedField(
        many=True, slug_field="image_url", read_only=True
    )
    # Accept a list of image URLs on create; these will be persisted as ProductImage
    image_urls = serializers.ListField(
        child=serializers.URLField(), write_only=True, required=False
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
            "image_urls",
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

    def get_seller(self, obj):
        return obj.get_seller_name()

    def create(self, validated_data):
        image_urls = validated_data.pop("image_urls", [])
        categories = validated_data.pop("categories", None)

        product = Product.objects.create(**validated_data)
        if categories is not None:
            product.categories.set(categories)

        if image_urls:
            images = [
                ProductImage(product=product, image_url=url) for url in image_urls
            ]
            ProductImage.objects.bulk_create(images)

        return product

    def update(self, instance, validated_data):
        image_urls = validated_data.pop("image_urls", None)
        categories = validated_data.pop("categories", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if categories is not None:
            instance.categories.set(categories)

        if image_urls is not None:
            instance.images.all().delete()
            images = [
                ProductImage(product=instance, image_url=url) for url in image_urls
            ]
            ProductImage.objects.bulk_create(images)

        return instance


class MinimalProductSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Product model.
    Includes only essential fields for cart display, including seller and first image.
    """

    seller = serializers.SerializerMethodField()
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
        return obj.get_seller_name()
