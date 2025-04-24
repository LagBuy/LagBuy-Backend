from rest_framework import serializers

from .models import CustomUser
from apps.riders.serializers import RidersSerializer

class CustomUserSerializer(serializers.ModelSerializer):
    """Custom user serializer class"""
    rider_profile = RidersSerializer()
    class Meta:
        model = CustomUser
        fields = (
            'id',
            'first_name',
            'last_name',
            'username',
            'email',
            'phone_number',
            'role',
            'image',
            'address',
            'created_at',
            'updated_at',
            'status',
            'is_active',
            'is_staff',
            'is_rider',
            'rider_profile',
        )
        read_only_fields = [
            'id',
            'email',
            'created_at',
            'updated_at',
            'is_staff',
        ]
