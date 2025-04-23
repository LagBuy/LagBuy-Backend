from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers

from apps.users.models import CustomUser
from apps.riders.models import Riders


class CustomRegisterSerializer(RegisterSerializer):
    """custom register serializer used by dj-rest-auth"""
    first_name = serializers.CharField(max_length=50, required=True)
    last_name = serializers.CharField(max_length=50, required=True)
    phone_number = serializers.CharField(max_length=20, required=True)
    role = serializers.ChoiceField(choices=[('buyer', 'Buyer'), ('seller', 'Seller'), ('dispatch', 'dispatch')], default='buyer')
    image = serializers.ImageField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_null=True)
    password2 = None
    is_rider = serializers.BooleanField(default=False)

    # riders info
    phone_number2 = serializers.CharField(max_length=20)
    nin = serializers.CharField(max_length=20)
    nok = serializers.CharField(max_length=50) # next of kin
    nok_phonenumber = serializers.CharField(max_length=20)
    motorcycle_type = serializers.CharField(max_length=10)
    motorcycle_brand = serializers.CharField(max_length=20)
    plate_number = serializers.CharField(max_length=20)
    guarantor1 = serializers.CharField(max_length=50)
    guarantor1_number = serializers.CharField(max_length=20)
    guarantor2 = serializers.CharField(max_length=50)
    guarantor2_number = serializers.CharField(max_length=20)
    bank_name = serializers.CharField(max_length=20)
    account_number = serializers.CharField(max_length=20)
    account_name = serializers.CharField(max_length=50)

    def validate(self, data):
        """Override the default behaviour of checking for
        password1 and password2"""
        return data

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data.update({
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'phone_number': self.validated_data.get('phone_number', ''),
            'role': self.validated_data.get('role', 'buyer'),
            'image': self.validated_data.get('image', None),
            'address': self.validated_data.get('address', None),
            'is_rider': self.validated_data.get('is_rider', False),
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
        user.is_rider = self.validated_data.get('is_rider', False)
        user.save()

        if user.is_rider == True:
            # use riders serializer for this to implement verification for bank, nin, etc
            Riders.objects.create(
                user=user,
                phone_number2=self.validated_data.get('phone_number2', ''),
                nin=self.validated_data.get('nin', ''),
                next_of_kin=self.validated_data.get('next_of_kin', ''),
                nok_phonenumber=self.validated_data.get('nok_phonenumber', ''),
                motorcycle_type=self.validated_data.get('motorcycle_type', ''),
                motorcycle_brand=self.validated_data.get('motorcycle_brand', ''),
                plate_number=self.validated_data.get('plate_number', ''),
                guarantor1=self.validated_data.get('guarantor1', ''),
                guarantor1_number=self.validated_data.get('guarantor1_number', ''),
                guarantor2=self.validated_data.get('guarantor2', ''),
                guarantor2_number=self.validated_data.get('guarantor2_number', ''),
                bank_name=self.validated_data.get('bank_name', ''),
                account_number=self.validated_data.get('account_number', ''),
                account_name=self.validated_data.get('account_name', ''),
            )

        return user

