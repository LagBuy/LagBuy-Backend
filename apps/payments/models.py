import datetime
import uuid

from django.db import models
from django.utils import timezone

from apps.userAuth.models import CustomUser
from apps.orders.models import Order


class Payment(models.Model):
    """Model to store and track all platform payment"""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    ref = models.UUIDField(unique=True)
    verified = models.BooleanField(default=False)
    currency = models.CharField(max_length=5)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Relationships
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="payments"
    )
    order = models.OneToOneField(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payment'
    )

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["created_at"]
    
    def __str__(self):
        return f"Payment of N{self.amount} made by {self.user.user_profile.first_name}"

    def verify_payment(self):
        """verify the payment using paystack verify endpoint"""
        pass

