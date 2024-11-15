from rest_framework import serializers

from apps.products.models import Product

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "product", "buyer", "rating", "comment", "created_at"]
        read_only_fields = ["id", "buyer", "created_at"]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate(self, data):
        request = self.context["request"]
        if request.method == "POST":
            product_id = data.get("product")
            user = request.user
            if Review.objects.filter(product_id=product_id, buyer=user).exists():
                raise serializers.ValidationError(
                    "You have already reviewed this product."
                )
        elif request.method in ["PUT", "PATCH"] and "product" in data:
            raise serializers.ValidationError(
                {"product": "Updating the product is not allowed."}
            )
        return data

    def create(self, validated_data):
        product_id = self.context["request"].data.get("product")
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise serializers.ValidationError({"product": "Invalid product ID."})
        validated_data["product"] = product
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Only allow updating the rating and comment fields
        instance.rating = validated_data.get("rating", instance.rating)
        instance.comment = validated_data.get("comment", instance.comment)
        instance.save()
        return instance

    def to_internal_value(self, data):
        request = self.context["request"]
        if request.method in ["PUT", "PATCH"]:
            # Remove the product field from required fields during update
            self.fields["product"].required = False
        return super().to_internal_value(data)
