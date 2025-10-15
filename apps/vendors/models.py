from decimal import Decimal
import uuid

from django.db import models
from django.utils import timezone
from django.db.models import JSONField

from apps.userAuth.models import CustomUser


class VendorWallet(models.Model):
    """Simple wallet model for vendors.

    - Each vendor (CustomUser) has one wallet.
    - Balance is stored as Decimal and updated atomically via F expressions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="vendor_wallet"
    )
    balance = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    currency = models.CharField(max_length=5, default="NGN")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vendor Wallet"
        verbose_name_plural = "Vendor Wallets"

    def __str__(self):
        return f"Wallet[{self.vendor.email}]: {self.balance} {self.currency}"

    def credit(self, amount, currency: str = "NGN"):
        """Credit the vendor wallet with `amount` (Decimal or numeric).

        Returns the new balance as Decimal.
        """
        from django.db.models import F

        if amount is None:
            return self.balance
        # ensure Decimal
        amount = Decimal(str(amount))
        # simple currency check - no conversion performed here
        if currency and self.currency != currency:
            # if currencies mismatch, we still credit but keep wallet currency
            pass
        # atomic update
        self.__class__.objects.filter(pk=self.pk).update(balance=F("balance") + amount)
        # refresh from db
        self.refresh_from_db(fields=["balance"])
        return self.balance

    def debit(self, amount, currency: str = "NGN"):
        """Debit the vendor wallet; raises ValueError on insufficient funds."""
        amount = Decimal(str(amount))
        if amount > self.balance:
            raise ValueError("Insufficient wallet balance")
        from django.db.models import F

        self.__class__.objects.filter(pk=self.pk).update(balance=F("balance") - amount)
        self.refresh_from_db(fields=["balance"])
        return self.balance


class VendorWithdrawal(models.Model):
    """
    Tracks all withdrawals, amounts, and status.
    Makes the system robust and auditable
    """

    vendor = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("completed", "Completed")],
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)


class ExportJob(models.Model):
    """
    Tracks jobs so background worker can process and
    WE can expose job listing/history if needed.
    """

    FORMAT_CSV = "csv"
    FORMAT_PDF = "pdf"
    FORMAT_CHOICES = [(FORMAT_CSV, "CSV"), (FORMAT_PDF, "PDF")]

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="export_jobs"
    )
    export_type = models.CharField(max_length=50, default="transactions")
    export_format = models.CharField(
        max_length=10, choices=FORMAT_CHOICES, default=FORMAT_CSV
    )
    params = JSONField(default=dict, blank=True)  # store filters like date range
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    file_name = models.TextField(null=True, blank=True)
    file_url = models.URLField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"ExportJob({self.id}) {self.user.email} {self.export_format} {self.status}"
        )


# -- Audit log model --
class AuditLog(models.Model):
    """
    Model to log sensitive actions as they are
    carried out, suspending user, changing plans etc
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        CustomUser,
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=255)
    target = models.CharField(max_length=255, null=True, blank=True)  # e.g. Vendor[id]
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        who = self.user.email if self.user else "system"
        return f"{self.created_at.isoformat()} {who} - {self.action}"
