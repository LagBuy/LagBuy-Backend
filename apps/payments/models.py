import uuid

from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.db import transaction

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
    # Whether vendor wallets have been credited for this payment
    wallet_credited = models.BooleanField(default=False)

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


class EscrowStatus(models.TextChoices):
    HELD = "held", "Held"
    RELEASED = "released", "Released"
    REFUNDED = "refunded", "Refunded"


class Escrow(models.Model):
    """Represents funds held in escrow for an order until release or refund.

    Business rules implemented here are intentionally minimal:
    - An Escrow is created when a Payment is successfully verified.
    - Funds remain HELD until explicitly released, at which point vendor wallets are
      credited via the existing distribute_payment_to_vendors utility.
    - Refunds are handled locally by marking the escrow refunded; integrating
      with the payment gateway for automated refunds should be added separately.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, related_name="escrow", null=True, blank=True
    )
    order = models.OneToOneField(
        "apps.orders.Order", on_delete=models.CASCADE, related_name="escrow"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=5, default="NGN")
    status = models.CharField(
        max_length=20, choices=EscrowStatus.choices, default=EscrowStatus.HELD
    )
    created_at = models.DateTimeField(default=timezone.now)
    released_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Escrow"
        verbose_name_plural = "Escrows"

    def __str__(self):
        return f"Escrow[{self.id}] for Order {self.order_id} ({self.status})"

    def release(self):
        """Release escrowed funds to vendors using the existing distributor.

        Returns the mapping of vendor credits on success.
        """
        if self.status != EscrowStatus.HELD:
            raise ValueError("Cannot release an escrow that is not held.")

        from .utils import distribute_payment_to_vendors

        with transaction.atomic():
            result = distribute_payment_to_vendors(self.order)
            # mark payment as wallet_credited if attached
            if self.payment:
                self.payment.wallet_credited = True
                self.payment.save(update_fields=["wallet_credited"])
            self.status = EscrowStatus.RELEASED
            self.released_at = timezone.now()
            self.save(update_fields=["status", "released_at"])
        return result

    def refund(self):
        """Mark escrow as refunded locally.

        Note: This method does not call the payment gateway. Implement gateway
        integration if automatic refunds should be issued from the platform.
        """
        if self.status != EscrowStatus.HELD:
            raise ValueError("Cannot refund an escrow that is not held.")
        with transaction.atomic():
            self.status = EscrowStatus.REFUNDED
            self.refunded_at = timezone.now()
            self.save(update_fields=["status", "refunded_at"])
