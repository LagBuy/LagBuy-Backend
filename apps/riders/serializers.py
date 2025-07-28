from rest_framework import serializers

from apps.orders.models import OrderItem
from apps.userAuth.models import CustomUser


class RiderOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model."""
    delivery_address = serializers.SerializerMethodField()
    pickup_address = serializers.SerializerMethodField()
    rider = serializers.SlugRelatedField(slug_field='email', queryset=CustomUser.objects.all())

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "rider", "delivery_address", "pickup_address", "ready_for_pickup", "picked_up", "delivery_status"]
        read_only_fields = fields.copy()

    def get_delivery_address(self, obj):
        address = obj.order.delivery_address
        return address
    
    def get_pickup_address(self, obj):
        address = obj.product.seller.vendor_profile.address
        return address


class AdminRiderOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model."""
    delivery_address = serializers.SerializerMethodField()
    rider = serializers.SlugRelatedField(slug_field='email', queryset=CustomUser.objects.all())
    assigned_riders = serializers.PrimaryKeyRelatedField(many=True, queryset=CustomUser.objects.all())

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "rider", "assigned_riders", "delivery_address", "ready_for_pickup", "picked_up", "delivery_status"]
        read_only_fields = fields.copy()

    def get_delivery_address(self, obj):
        address = obj.order.delivery_address
        return address


class UpdateOrderItemAssignedRidersSerializer(serializers.ModelSerializer):
    """Serializer to update the assigned riders to each order"""
    assigned_riders = serializers.PrimaryKeyRelatedField(many=True, queryset=CustomUser.objects.all())

    class Meta:
        model = OrderItem
        fields = ["assigned_riders"]
    
    def validate_assigned_riders(self, value):
        """Ensure that the added user is a rider"""
        for user in value:
            if 'rider' not in [i.name for i in user.roles.all()]:
                raise serializers.ValidationError("User must be a registered rider")
        return value        

    def validate(self, attrs):
        """Validate and throw error when item is:
        - not ready for pickup
        - already delivered
        """
        if not self.instance.ready_for_pickup:
            raise serializers.ValidationError("Item not ready for pickup")
        if self.instance.delivery_status == OrderItem.DeliveryStatus.DELIVERED:
            raise serializers.ValidationError("Item already delivered")

        return attrs
