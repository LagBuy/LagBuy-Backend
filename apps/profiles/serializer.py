from rest_framework import serializers

from .models import UsersProfile, VendorsProfile, RidersProfile

class UserProfileSerializer(serializers.ModelSerializer):
    """Custom user serializer class"""

    class Meta:
        model = UsersProfile
        fields = (
            'first_name',
            'last_name',
            'phone_number',
            'image',
            'address',
            'gender',
            'dob',
            'state',
            'city',
        )


class VendorProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = VendorsProfile
        fields = (
            'business_name',
            'business_location_city',
            'business_location_state',
            'is_verified'
        )
        read_only_fields = [
            'is_verified',
        ]


class RiderProfileSerializer(serializers.ModelSerializer):
    """Riders serializer class"""
    class Meta:
        model = RidersProfile
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
            'is_verified',
        )
        read_only_fields = [
            'is_verified',
        ]

