import uuid

from django.db import models
from django.utils import timezone

from apps.orders.models import Order
from apps.userAuth.models import CustomUser

from .services import payment_service


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


class Payment(models.Model):
    """Model to store and track all platform payment"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    ref = models.CharField(
        max_length=100, unique=True, help_text="Unique reference for the payment"
    )
    verified = models.BooleanField(default=False)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        help_text="Status of the payment",
    )
    currency = models.CharField(max_length=5)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now_add=True)

    # Relationships
    user = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, related_name="payments"
    )
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, related_name="payments"
    )

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["created_at"]

    def __str__(self):
        return f"Payment of N{self.amount} made by {self.user.user_profile.first_name} [{self.payment_status}]"

    def verify_payment(self):
        """
        Verifies the payment associated with this instance using the PaymentService.
        """
        return payment_service.verify_payment(self.ref)


class PayoutRequest(models.Model):
    """Model to handle payout requests to vendors"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=5)
    requested_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    # Whether this payout request was made as a priority (immediate) request
    is_priority = models.BooleanField(default=False)
    # Flat fee applied for priority withdrawals (stored in same currency as amount)
    priority_fee = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    # Net amount after fee (for record keeping)
    net_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        help_text="Status of the payout request",
    )

    # Relationships
    vendor = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="payout_requests"
    )

    class Meta:
        verbose_name = "Payout Request"
        verbose_name_plural = "Payout Requests"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Payout Request of N{self.amount} by {self.vendor.user_profile.first_name} [{self.status}]"
