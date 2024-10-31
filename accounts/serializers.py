from rest_framework import serializers

from .models import CustomUser

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
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
        model = CustomUser

# serialize relationship fields
