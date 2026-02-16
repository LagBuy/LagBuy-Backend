import uuid
import secrets

from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from apps.products.models import Product
from apps.userAuth.models import CustomUser


class UsersProfile(models.Model):
    """Buyers Profile"""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False
    )
    first_name = models.CharField(max_length=225)
    last_name = models.CharField(max_length=225)
    phone_number = models.CharField(max_length=20, null=False, unique=True)
    phone_verified = models.BooleanField(default=False)
    phone_verification_code = models.CharField(max_length=6, null=True, blank=True)
    phone_code_expires_at = models.DateTimeField(null=True, blank=True)
    gender = models.CharField(max_length=20, null=True)
    dob = models.DateField(null=True)
    state = models.CharField(max_length=20, null=True)
    city = models.CharField(max_length=20, null=True)
    address = models.TextField(null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    image = models.URLField(max_length=500, null=True, blank=True)

    # Relationships
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="user_profile"
    )
    viewed_products = models.ManyToManyField(
        Product, related_name="viewers", blank=True
    )  # viewed products by the user. only store recently viewed products
    favorite_vendors = models.ManyToManyField(
        CustomUser, related_name="fans", blank=True
    )  # favorite vendors by the user

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "Users Profile"

    def __str__(self):
        """object return string"""
        return f"User Profile: {self.first_name} {self.last_name} [{self.user.email}]"

    def generate_phone_verification_code(self):
        """Generate a 6-digit OTP for phone verification"""
        code = str(secrets.randbelow(1000000)).zfill(6)
        self.phone_verification_code = code
        self.phone_code_expires_at = timezone.now() + timezone.timedelta(minutes=10)
        self.save()
        return code

    def is_phone_code_valid(self, code):
        """Check if the provided code is valid and not expired"""
        if not self.phone_verification_code or not self.phone_code_expires_at:
            return False
        
        if timezone.now() > self.phone_code_expires_at:
            return False
        
        return self.phone_verification_code == code

    def verify_phone(self, code):
        """Verify phone number with the provided code"""
        if not self.is_phone_code_valid(code):
            return False
        
        self.phone_verified = True
        self.phone_verification_code = None
        self.phone_code_expires_at = None
        self.save()
        return True


class VendorsProfile(models.Model):
    """Seller Profile"""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False
    )
    business_name = models.CharField(null=True, max_length=225)
    business_address = models.TextField(null=True)
    business_location_city = models.CharField(max_length=225, null=True)
    business_location_state = models.CharField(max_length=225, null=True)

    is_verified = models.BooleanField(default=False)
    # Paystack transfer recipient code. Populate when creating transfer recipients.
    transfer_recipient = models.CharField(max_length=255, null=True, blank=True)

    # Bank code and account number for vendor payouts
    bank_code = models.CharField(max_length=20, null=True, blank=True)
    account_number = models.CharField(max_length=20, null=True, blank=True)

    is_suspended = models.BooleanField(default=False)
    PLAN_CHOICES = [
        ("basic", "Basic"),
        ("premium", "Premium"),
        ("enterprise", "Enterprise"),
    ]
    plan_type = models.CharField(max_length=50, choices=PLAN_CHOICES, default="basic")

    # Relationships
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="vendor_profile"
    )

    class Meta:
        verbose_name = "Vendor Profile"
        verbose_name_plural = "Vendors Profile"
        constraints = [
            models.UniqueConstraint(
                Lower("business_name"),
                name="unique_lower_business_name_constraint",
                violation_error_message="A vendor with this business name already exists.",
            )
        ]
        indexes = [
            models.Index(fields=['business_name']),
        ]

    def __str__(self):
        """object return string"""
        return f"Vendor: {self.business_name} [{self.user.email}]"

    @property
    def address(self):
        """get the full vendor address"""
        text = (
            f"{self.business_address if self.business_address else ''}, "
            f"{self.business_location_city if self.business_location_city else ''}, "
            f"{self.business_location_state if self.business_location_state else ''}"
        )
        return text.rstrip().rstrip(",").rstrip().rstrip(",")

    @property
    def short_address(self):
        """get the vendor city and state"""
        text = (
            f"{self.business_location_city if self.business_location_city else ''}, "
            f"{self.business_location_state if self.business_location_state else ''}"
        )
        return text.rstrip().rstrip(",")


class RidersProfile(models.Model):
    """A custom user class to manage all riders specific informations"""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False
    )
    phone_number2 = models.CharField(max_length=20, null=True)
    nin = models.CharField(max_length=20, null=True)
    next_of_kin = models.CharField(max_length=225, null=True)  # next of kin
    nok_phonenumber = models.CharField(max_length=20, null=True)
    motorcycle_type = models.CharField(max_length=225, null=True)
    motorcycle_brand = models.CharField(max_length=225, null=True)
    plate_number = models.CharField(max_length=20, null=True)
    guarantor1 = models.CharField(max_length=225, null=True)
    guarantor1_number = models.CharField(max_length=20, null=True)
    guarantor2 = models.CharField(max_length=225, null=True)
    guarantor2_number = models.CharField(max_length=20, null=True)
    bank_name = models.CharField(max_length=225, null=True)
    account_number = models.CharField(max_length=20, null=True)
    account_name = models.CharField(max_length=225, null=True)

    is_verified = models.BooleanField(default=False)

    # Relationships
    # TODO: add one to many relationship to order items
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="rider_profile"
    )

    class Meta:
        verbose_name = "Rider Profile"
        verbose_name_plural = "Riders Profile"

    def __str__(self):
        """object return string"""
        return f"Rider: [{self.user.email}]"
