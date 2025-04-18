from django.db import models
import uuid
import datetime
from django.utils import timezone
from apps.users.models import CustomUser
from apps.products.models import Product

class Coupon(models.Model):
    """Model representing a coupon"""
    class DiscountType(models.TextChoices):
        """Choises for the discount type"""
        FIXED = "FIXED", "Fixed"
        PERCENT = "PERCENT", "Percentage"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices, default=DiscountType.FIXED)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, blank=False)
    min_purchase_quantity = models.PositiveIntegerField(null=True)
    max_purchase_quantity = models.PositiveIntegerField(null=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(null=True)
    used_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    seller = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='coupons')
    """list of products the coupon is valid on. Must be the seller's products"""
    products = models.ManyToManyField(Product, related_name='coupons') # TODO: remove and add to the Product model itself. a product has coupons, a coupon does not have products

    @property
    def status(self):
        """Get the status of a coupon, if it is still valid or not"""
        if self.valid_to < timezone.now():
            return False
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False
        return True

    class Meta:
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'
        ordering = ['-created_at']

    def __str__(self):
        """object return string"""
        return f"Coupon - {self.code} by {self.seller}"
