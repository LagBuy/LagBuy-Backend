from rest_framework import serializers
from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "payment_status",
            "delivery_status",
            "delivery_fee",
            "total_price",
        ]

    def create(self, validated_data):
        delivery_fee = self.calculate_delivery_fee(validated_data)
        total_price = self.calculate_total_price(validated_data, delivery_fee)

        validated_data["delivery_fee"] = delivery_fee
        validated_data["total_price"] = total_price
        validated_data["payment_status"] = Order.PaymentStatus.PENDING
        validated_data["delivery_status"] = Order.DeliveryStatus.PENDING

        return super().create(validated_data)

    def calculate_delivery_fee(self, validated_data):
        return 10.00

    def calculate_total_price(self, validated_data, delivery_fee):
        products = validated_data["products"]
        total_price = sum(product.price for product in products) + delivery_fee
        return total_price
