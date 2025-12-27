import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class ReferralWallet(models.Model):
    """
    One wallet per user. Holds no business logic for balances directly
    Balances are derived from transactions(approved referrals).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_wallet",
    )

    class Meta:
        verbose_name = "Referral Wallet"
        verbose_name_plural = "Referral Wallets"

    def __str__(self) -> str:
        return f"ReferralWallet[{self.user.email}]"


class ReferralWalletTransaction(models.Model):
    """
    Immutable ledger of all referral wallet activity.
    """

    class TransactionType(models.TextChoices):
        ADDITION = "addition", "Addition"
        DEDUCTION = "deduction", "Deduction"
        PENDING = "pending", "Pending"

    class BonusUsageType(models.TextChoices):
        PRODUCT = "product", "Product Purchase"
        SERVICE = "service", "Service Charge"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    wallet = models.ForeignKey(
        ReferralWallet, on_delete=models.CASCADE, related_name="transactions"
    )

    amount = models.DecimalField(max_digits=18, decimal_places=2)

    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)

    bonus_usage_type = models.CharField(max_length=20, choices=BonusUsageType.choices)

    # Optional relations
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referral_wallet_transactions",
    )

    referred_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referral_earnings",
    )
    description = models.CharField(max_length=255)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["bonus_usage_type"]),
        ]

    def __str__(self):
        return (
            f"{self.transaction_type.upper()} {self.amount} ({self.bonus_usage_type})"
        )
