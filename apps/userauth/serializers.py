from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers

from apps.users.models import CustomUser


class CustomRegisterSerializer(RegisterSerializer):
    """custom register serializer used by dj-rest-auth"""
    first_name = serializers.CharField(max_length=50, required=True)
    last_name = serializers.CharField(max_length=50, required=True)
    phone_number = serializers.CharField(max_length=20, required=True)
    role = serializers.ChoiceField(choices=[('buyer', 'Buyer'), ('seller', 'Seller'), ('dispatch', 'dispatch')], default='buyer')
    image = serializers.ImageField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_null=True)

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data.update({
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'phone_number': self.validated_data.get('phone_number', ''),
            'role': self.validated_data.get('role', 'buyer'),
            'image': self.validated_data.get('image', None),
            'address': self.validated_data.get('address', None),
        })
        return data
    
    def save(self, request):
        user = super().save(request)
        user.first_name = self.validated_data.get('first_name', '')
        user.last_name = self.validated_data.get('last_name', '')
        user.phone_number = self.validated_data.get('phone_number', '')
        user.role = self.validated_data.get('role', 'buyer')
        user.image = self.validated_data.get('image', None)
        user.address = self.validated_data.get('address', None)
        user.save()
        return user

