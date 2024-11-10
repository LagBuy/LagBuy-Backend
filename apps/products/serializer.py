"""Serializer for Product view"""

from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    seller = serializers.StringRelatedField()
    carts = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    categories = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    orders = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    reviews = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'seller',
            'name',
            'description',
            'price',
            'images',
            'verified',
            'stock_quantity',
            'created_at',
            'updated_at',
            'carts',
            'categories',
            'orders',
            'reviews',
        ]
        read_only_fields = ['id', 'seller', ]