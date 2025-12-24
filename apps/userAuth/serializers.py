from django.db import IntegrityError
from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import PasswordResetSerializer

from .models import CustomUser, Role
from common.utils.custom_exceptions import UserAlreadyExist
from apps.userAuth.models import CustomUser
from apps.profiles.models import UsersProfile, VendorsProfile, RidersProfile
from apps.profiles.serializer import (UserProfileSerializer,
                                      VendorProfileSerializer,
                                      RiderProfileSerializer)


class CustomRegisterSerializer(RegisterSerializer):
    """custom register serializer used by dj-rest-auth"""

    #roles = serializers.ListField(child=serializers.CharField(), default=['user'], write_only=True)
    roles = serializers.SlugRelatedField(
        many=True, slug_field='name', queryset=Role.objects.all(), required=False
    )

    # user profile
    first_name = serializers.CharField(max_length=225, required=True)
    last_name = serializers.CharField(max_length=225, required=True)
    phone_number = serializers.CharField(max_length=20, required=True)
    image = serializers.URLField(max_length=500, required=False, allow_null=True, allow_blank=True)
    address = serializers.CharField(max_length=225, required=False, allow_null=True)
    gender = serializers.CharField(max_length=20, required=False, allow_null=True)
    dob = serializers.DateField(required=False, allow_null=True)
    state = serializers.CharField(max_length=20, required=False, allow_null=True)
    city = serializers.CharField(max_length=20, required=False, allow_null=True)
    password2 = None

    # vendor profile
    business_name = serializers.CharField(max_length=225, required=False)
    business_address = serializers.CharField(max_length=225, required=False)
    business_location_city = serializers.CharField(max_length=225, required=False)
    business_location_state = serializers.CharField(max_length=225, required=False)

    # riders info
    phone_number2 = serializers.CharField(max_length=20, required=False)
    nin = serializers.CharField(max_length=20, required=False)
    next_of_kins = serializers.CharField(max_length=225, required=False) # next of kin
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


    def validate_phone_number(self, value):
        """Validate that the phone number is not already registered"""
        if UsersProfile.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return value

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
            'roles': self.validated_data.get('roles', []),
            'image': self.validated_data.get('image', None),
            'address': self.validated_data.get('address', None),
        })
        return data

    def save(self, request):
        roles = self.validated_data.get('roles', [])
        roles = [i.name for i in roles]

        roles.append('user')
        roles = list(set(roles)) # TODO: test if this is necessary

        # TODO: add logic to check if the user exist first and 
        # just update the user model with the rider or seller profile
        # without touching the user profile. but check first to ensure
        # the seller or rider profile do not already exist (i guess you 
        # can use the update serializer)
        
        try:
            user = super().save(request)

            for role_name in roles:
                if role_name in ['user', 'vendor', 'rider']:
                    role, _ = Role.objects.get_or_create(name=role_name.lower())
                    user.roles.add(role)

            try:
                UsersProfile.objects.create(
                    user=user,
                    first_name=self.validated_data.get('first_name', ''),
                    last_name=self.validated_data.get('last_name', ''),
                    phone_number=self.validated_data.get('phone_number', ''),
                    image=self.validated_data.get('image', None),
                    address=self.validated_data.get('address', None),
                    gender=self.validated_data.get('gender', ''),
                    dob=self.validated_data.get('dob'),
                    city=self.validated_data.get('city', ''),
                    state=self.validated_data.get('state', '')
                )
            except Exception as e:
                user.delete()
                raise e


            if 'vendor' in roles:
                try:
                    VendorsProfile.objects.create(
                        user=user,
                        business_name=self.validated_data.get('business_name', ''),
                        business_address=self.validated_data.get('business_address', ''),
                        business_location_city=self.validated_data.get('business_location_city', ''),
                        business_location_state=self.validated_data.get('business_location_state', '')
                    )
                except IntegrityError as e:
                    user.delete()
                    if "business_name" in str(e):
                        raise serializers.ValidationError({"business_name": "A vendor with this business name already exists."})
                    raise e
                except Exception as e:
                    user.delete()
                    raise e

            if 'rider' in roles:
                try:
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
                except Exception as e:
                    user.delete()
                    raise e

            return user
        except IntegrityError as e:
            # raise a custom exception if the user already exists
            if "email" in str(e):
                raise UserAlreadyExist()
            raise e

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
        read_only_fields = ['email', 'is_active']

    # TODO: Disable the PUT method, only PATCH should work
    def update(self, instance, validated_data):
        '''Update a user profile'''
        roles_data = validated_data.pop('roles', [])
        roles_data = [i.name for i in roles_data]

        user_current_roles = [i.name for i in instance.roles.all()]
        roles = set(roles_data).difference(user_current_roles)

        for role_name in roles:
            if role_name in ['user', 'vendor', 'rider']:
                if role_name in user_current_roles:
                    continue
                role, _ = Role.objects.get_or_create(name=role_name.lower())
                instance.roles.add(role)
        
        # TODO: use their serializers for proper validation and update
        user_profile_data = validated_data.pop('user_profile', {})
        user_profile, created = UsersProfile.objects.get_or_create(user=instance)
        for key, value in user_profile_data.items():
            setattr(user_profile, key, value)
        user_profile.save()

        if 'vendor' in user_current_roles or 'vendor' in roles:
            vendor_profile_data = validated_data.pop('vendor_profile', {})
            vendor_profile, created = VendorsProfile.objects.get_or_create(user=instance)
            for key, value in vendor_profile_data.items():
                setattr(vendor_profile, key, value)
            vendor_profile.save()

        if 'rider' in user_current_roles or 'rider' in roles:
            rider_profile_data = validated_data.pop('rider_profile', {})
            rider_profile, created = RidersProfile.objects.get_or_create(user=instance)
            for key, value in rider_profile_data.items():
                setattr(rider_profile, key, value)
            rider_profile.save()
        
        return instance

