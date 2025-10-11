from decimal import Decimal
import uuid

from django.db import models
from django.utils import timezone

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
