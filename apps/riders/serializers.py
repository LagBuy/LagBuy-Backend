from rest_framework import serializers

from .models import Riders

class RidersSerializer(serializers.ModelSerializer):
    """Custom user serializer class"""
    class Meta:
        model = Riders
        fields = (
            'phone_number2',
            'nin',
            'next_of_kin',
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
            'is_active',
        )
        read_only_fields = [
            'is_active',
        ]

