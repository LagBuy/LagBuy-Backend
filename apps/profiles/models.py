from django.db import models
from django.utils import timezone
import uuid

from apps.users.models import CustomUser


class UsersProfile(models.Model):
    """Buyers Profile"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, null=False)
    first_name = models.CharField(max_length=225)
    last_name = models.CharField(max_length=225)
    phone_number = models.CharField(max_length=20, null=False)
    address = models.TextField(null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    image = models.ImageField(upload_to='profile_image/', null=True, blank=True)

    # Relationships
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='user_profile')

    class Meta:
        verbose_name = "Vendor Profile"
        verbose_name_plural = "Vendors Profile"

    def __str__(self):
        """object return string"""
        return f'User Profile: {self.user.first_name} {self.user.last_name} [{self.user.email}]'


class VendorsProfile(models.Model):
    """Seller Profile"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, null=False)
    business_name = models.CharField(null=True, max_length=225, unique=True)
    business_location_city = models.CharField(max_length=225, null=True)
    business_location_state = models.CharField(max_length=225, null=True)

    is_verified = models.BooleanField(default=False)

    # Relationships
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='vendor_profile')

    class Meta:
        verbose_name = "Vendor Profile"
        verbose_name_plural = "Vendors Profile"

    def __str__(self):
        """object return string"""
        return f'Vendor: {self.user.first_name} {self.user.last_name} [{self.user.email}]'


class RidersProfile(models.Model):
    """A custom user class to manage all riders specific informations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, null=False)
    phone_number2 = models.CharField(max_length=20)
    nin = models.CharField(max_length=20, null=False)
    next_of_kin = models.CharField(max_length=225) # next of kin
    nok_phonenumber = models.CharField(max_length=20)
    motorcycle_type = models.CharField(max_length=225)
    motorcycle_brand = models.CharField(max_length=225)
    plate_number = models.CharField(max_length=20)
    guarantor1 = models.CharField(max_length=225)
    guarantor1_number = models.CharField(max_length=20)
    guarantor2 = models.CharField(max_length=225)
    guarantor2_number = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=225)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=225)

    is_verified = models.BooleanField(default=False)

    # Relationships
    # TODO: add one to many relationship to order items
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='rider_profile')

    class Meta:
        verbose_name = "Rider Profile"
        verbose_name_plural = "Riders Profile"

    def __str__(self):
        """object return string"""
        return f'Rider: {self.user.first_name} {self.user.last_name} [{self.user.email}]'


