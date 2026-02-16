from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from common.services.storage import STORAGE
from apps.profiles.models import UsersProfile
from apps.profiles.serializer import (
    SendPhoneVerificationCodeSerializer,
    VerifyPhoneCodeSerializer,
    ResendPhoneVerificationCodeSerializer
)


class ImageUploadView(APIView):
    """
    API endpoint for uploading product images.
    Handles file uploads and returns the image URL on success.
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        try:
            uploaded_image = request.FILES.get("image")
            if not uploaded_image:
                return Response(
                    {"detail": "No image file provided."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            file_url = STORAGE.upload_file(
                uploaded_image, uploaded_image.name, uploaded_image.content_type
            )
            if file_url:
                return Response({"url": file_url}, status=status.HTTP_201_CREATED)
            return Response(
                {"detail": "Failed to upload image."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            raise e  # allows for proper flagging and debugging


class SendPhoneVerificationCodeView(APIView):
    """
    API endpoint for sending phone verification code.
    Users receive a 6-digit OTP via SMS/Email to verify their phone number.
    """

    def post(self, request, *args, **kwargs):
        serializer = SendPhoneVerificationCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data['phone_number']

        try:
            user_profile = UsersProfile.objects.get(phone_number=phone_number)
        except UsersProfile.DoesNotExist:
            # Return generic message to prevent enumeration
            return Response(
                {"detail": "Verification code has been sent if the phone number exists."},
                status=status.HTTP_200_OK
            )

        # Check if already verified
        if user_profile.phone_verified:
            return Response(
                {"detail": "This phone number is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate and send verification code
        verification_code = user_profile.generate_phone_verification_code()

        # TODO: Send verification code via SMS/Email
        # Example: send_sms_verification_code(phone_number, verification_code)
        # Use services like Twilio, AWS SNS, or any SMS provider

        return Response(
            {"detail": "Verification code sent to your phone number."},
            status=status.HTTP_200_OK
        )


class VerifyPhoneCodeView(APIView):
    """
    API endpoint for verifying phone number with OTP code.
    User submits the code received via SMS/Email to verify their phone number.
    """

    def post(self, request, *args, **kwargs):
        serializer = VerifyPhoneCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']

        try:
            user_profile = UsersProfile.objects.get(phone_number=phone_number)
        except UsersProfile.DoesNotExist:
            return Response(
                {"detail": "Phone number not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if already verified
        if user_profile.phone_verified:
            return Response(
                {"detail": "This phone number is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify the code
        if user_profile.verify_phone(code):
            return Response(
                {"detail": "Phone number verified successfully."},
                status=status.HTTP_200_OK
            )

        return Response(
            {"detail": "Invalid or expired verification code."},
            status=status.HTTP_400_BAD_REQUEST
        )


class ResendPhoneVerificationCodeView(APIView):
    """
    API endpoint for resending phone verification code.
    User can request a new OTP if the previous one expired.
    """

    def post(self, request, *args, **kwargs):
        serializer = ResendPhoneVerificationCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data['phone_number']

        try:
            user_profile = UsersProfile.objects.get(phone_number=phone_number)
        except UsersProfile.DoesNotExist:
            # Return generic message to prevent enumeration
            return Response(
                {"detail": "Verification code has been sent if the phone number exists."},
                status=status.HTTP_200_OK
            )

        # Check if already verified
        if user_profile.phone_verified:
            return Response(
                {"detail": "This phone number is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate and send new verification code
        verification_code = user_profile.generate_phone_verification_code()

        # TODO: Send verification code via SMS/Email
        # Example: send_sms_verification_code(phone_number, verification_code)

        return Response(
            {"detail": "New verification code sent to your phone number."},
            status=status.HTTP_200_OK
        )


class PhoneVerificationStatusView(APIView):
    """
    API endpoint to check phone verification status.
    Requires authentication.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user_profile = request.user.user_profile
        except UsersProfile.DoesNotExist:
            return Response(
                {"detail": "User profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "phone_number": user_profile.phone_number,
                "phone_verified": user_profile.phone_verified,
            },
            status=status.HTTP_200_OK
        )
