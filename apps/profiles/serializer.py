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
            "phone_verified",
            "image",
            "address",
            "gender",
            "dob",
            "state",
            "city",
        )
        read_only_fields = (
            "phone_verified",
        )


class VendorProfileSerializer(serializers.ModelSerializer):
    # return the vendor owner's profile image (UsersProfile.image)
    image = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = VendorsProfile
        fields = (
            "business_name",
            "business_address",
            "business_location_city",
            "business_location_state",
            "is_verified",
            "image",
        )
        read_only_fields = [
            "is_verified",
            "image",
        ]

    def get_image(self, obj):
        """Return the related user's profile image URL if available."""
        # VendorsProfile -> user (CustomUser) -> user_profile (UsersProfile)
        user = getattr(obj, "user", None)
        if not user:
            return None
        profile = getattr(user, "user_profile", None)
        if not profile:
            return None
        return profile.image


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


class SendPhoneVerificationCodeSerializer(serializers.Serializer):
    """Serializer for sending phone verification code"""
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        """Validate that phone number is not already verified and registered"""
        try:
            user_profile = UsersProfile.objects.get(phone_number=value)
            if user_profile.phone_verified:
                raise serializers.ValidationError(
                    "This phone number is already verified on another account."
                )
        except UsersProfile.DoesNotExist:
            pass
        return value


class VerifyPhoneCodeSerializer(serializers.Serializer):
    """Serializer for verifying phone code"""
    phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6, min_length=6)

    def validate_code(self, value):
        """Validate that code is numeric"""
        if not value.isdigit():
            raise serializers.ValidationError("Verification code must be numeric.")
        return value


class ResendPhoneVerificationCodeSerializer(serializers.Serializer):
    """Serializer for resending phone verification code"""
    phone_number = serializers.CharField(max_length=20)
