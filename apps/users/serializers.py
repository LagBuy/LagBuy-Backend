from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer

from .models import CustomUser, Role
from apps.users.models import CustomUser
from apps.profiles.models import UsersProfile, VendorsProfile, RidersProfile
from apps.profiles.serializer import (UserProfileSerializer,
                                      VendorProfileSerializer,
                                      RiderProfileSerializer)


class CustomRegisterSerializer(RegisterSerializer):
    """custom register serializer used by dj-rest-auth"""

    roles = serializers.ListField(child=serializers.CharField(), default=['user'], write_only=True)

    # user profile
    first_name = serializers.CharField(max_length=225, required=True)
    last_name = serializers.CharField(max_length=225, required=True)
    phone_number = serializers.CharField(max_length=20, required=True)
    image = serializers.ImageField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_null=True)
    password2 = None

    # vendor profile
    business_name = serializers.CharField(max_length=225, required=False)
    business_location_city = serializers.CharField(max_length=225, required=False)
    business_location_state = serializers.CharField(max_length=225, required=False)

    # riders info
    phone_number2 = serializers.CharField(max_length=20, required=False)
    nin = serializers.CharField(max_length=20, required=False)
    nok = serializers.CharField(max_length=225, required=False) # next of kin
    nok_phonenumber = serializers.CharField(max_length=20, required=False)
    motorcycle_type = serializers.CharField(max_length=225, required=False)
    motorcycle_brand = serializers.CharField(max_length=225, required=False)
    plate_number = serializers.CharField(max_length=20, required=False)
    guarantor1 = serializers.CharField(max_length=225, required=False)
    guarantor1_number = serializers.CharField(max_length=20, required=False)
    guarantor2 = serializers.CharField(max_length=225, required=False)
    guarantor2_number = serializers.CharField(max_length=20, required=False)
    bank_name = serializers.CharField(max_length=225, required=False)
    account_number = serializers.CharField(max_length=20, required=False)
    account_name = serializers.CharField(max_length=225, required=False)

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
            'roles': self.validated_data.get('roles', ['user']),
            'image': self.validated_data.get('image', None),
            'address': self.validated_data.get('address', None),
        })
        return data
    
    def save(self, request):
        roles = self.validated_data.get('roles', [])
        roles.append('user')

        user = super().save(request)

        UsersProfile.objects.create(
            user=user,
            first_name=self.validated_data.get('first_name', ''),
            last_name=self.validated_data.get('last_name', ''),
            phone_number=self.validated_data.get('phone_number', ''),
            image=self.validated_data.get('image', None),
            address=self.validated_data.get('address', None)
        )

        for role_name in roles:
            if role_name in ['user', 'vendor', 'rider']:
                role, _ = Role.objects.get_or_create(name=role_name.lower())
                user.roles.add(role)


        if 'vendor' in roles:
            VendorsProfile.objects.create(
                business_name=self.validated_data.get('business_name', ''),
                business_location_city=self.validated_data.get('business_location_city', ''),
                business_location_state=self.validated_data.get('business_location_state', '')
            )

        if 'rider' in roles:
            # use riders serializer for this to implement verification for bank, nin, etc
            RidersProfile.objects.create(
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


class CustomUserSerializer(serializers.ModelSerializer):
    """Custom user serializer class"""
    roles = serializers.SlugRelatedField(
        many=True, slug_field='name', queryset=Role.objects.all()
    )
    user_profile = UserProfileSerializer()
    vendor_profile = VendorProfileSerializer()
    rider_profile = RiderProfileSerializer()

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'email',
            'roles', # should be able to update the role
            'is_active',
            'user_profile',
            'vendor_profile',
            'rider_profile',
        )
        read_only_fields = ['email', 'is_active', 'vendor_profile', 'rider_profile']

    # TODO: create a custom update method

