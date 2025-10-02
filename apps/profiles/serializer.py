from rest_framework import serializers
from .models import UsersProfile, VendorsProfile, RidersProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """Custom user serializer class"""

    class Meta:
        model = UsersProfile
        fields = (
            "first_name",
            "last_name",
            "phone_number",
            "image",
            "address",
            "gender",
            "dob",
            "state",
            "city",
        )


class VendorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorsProfile
        fields = (
            "business_name",
            "business_address",
            "business_location_city",
            "business_location_state",
            "is_verified",
        )
        read_only_fields = [
            "is_verified",
        ]


class RiderProfileSerializer(serializers.ModelSerializer):
    """Riders serializer class"""

    class Meta:
        model = RidersProfile
        fields = (
            "phone_number2",
            "nin",
            "next_of_kin",
            "nok_phonenumber",
            "motorcycle_type",
            "motorcycle_brand",
            "plate_number",
            "guarantor1",
            "guarantor1_number",
            "guarantor2",
            "guarantor2_number",
            "bank_name",
            "account_number",
            "account_name",
            "is_verified",
        )
        read_only_fields = [
            "is_verified",
        ]


class VendorBankDetailsUpdateSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    account_number = serializers.CharField()
    bank_code = serializers.CharField()

    def validate_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                "Invalid password", code="invalid_password"
            )
        return value

    def validate_account_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Account number must be digits only.")
        # check length
        return value

    def update(self, instance, validated_data):
        # Remove password before updating vendor model
        validated_data.pop("password", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save(update_fields=validated_data.keys())
        return instance
