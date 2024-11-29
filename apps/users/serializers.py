from rest_framework import serializers

from .models import CustomUser

class CustomUserSerializer(serializers.ModelSerializer):
    """Custom user serializer class"""
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
        )
        read_only_fields = [
            'id',
            'email',
            'created_at',
            'updated_at',
            'is_staff',
        ]
