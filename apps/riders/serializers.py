from rest_framework import serializers

from .models import Riders

class RidersSerializer(serializers.ModelSerializer):
    """Custom user serializer class"""
    class Meta:
        model = Riders
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
            'phone_number2',
            'nin',
            'nok',
            'nok_phonenumber',
            'motorcycle_type',
            'motorcycle_brand',
            'plate_number',
            'guarantor1',
            'guarantor1_number',
            'guarantor2',
            'guarantor2_number',
            'bank_name',
            'account_number',
            'account_name',
            'status',
            # 'is_staff',
            # 'is_active'
        )
        read_only_fields = [
            'id',
            'email',
            'created_at',
            'updated_at',
            'status',
        ]


