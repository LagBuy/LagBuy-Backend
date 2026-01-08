import uuid
from decimal import Decimal
from django.db import models, transaction
from django.db.models import F
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

    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_used = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Referral Wallet"
        verbose_name_plural = "Referral Wallets"

    def _log_transaction(
        self,
        *,
        amount,
        transaction_type,
        description,
        bonus_usage_type=None,
        order=None,
        referred_user=None,
    ):
        ReferralWalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type=transaction_type,
            bonus_usage_type=bonus_usage_type,
            order=order,
            referred_user=referred_user,
            description=description,
        )

    @transaction.atomic
    def add_available_bonus(
        self, amount: Decimal, description: str = "", referred_user=None
    ):
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")

        self.__class__.objects.filter(pk=self.pk).update(
            available_balance=F("available_balance") + amount
        )
        self.refresh_from_db(fields=["available_balance"])

        # Log the TRX using FUNC
        self._log_transaction(
            amount=amount,
            transaction_type=ReferralWalletTransaction.TransactionType.ADDITION,
            description=description,
            referred_user=referred_user,
        )

    @transaction.atomic
    def add_pending_bonus(
        self, amount: Decimal, description: str = "", referred_user=None
    ):
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")

        self.__class__.objects.filter(pk=self.pk).update(
            pending_balance=F("pending_balance") + amount
        )
        self.refresh_from_db(fields=["pending_balance"])

        # Log the TRX using FUNC
        self._log_transaction(
            amount=amount,
            transaction_type=ReferralWalletTransaction.TransactionType.PENDING,
            description=description,
            referred_user=referred_user,
        )

    @transaction.atomic
    def deduct(
        self, amount: Decimal, description: str = "", usage_type=None, order=None
    ):
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if amount > self.available_balance:
            raise ValueError("Insufficient referall balance")

        self.__class__.objects.filter(pk=self.pk).update(
            available_balance=F("available_balance") - amount,
            total_used=F("total_used") + amount,
        )

        self.refresh_from_db(fields=["available_balance", "total_used"])
        
        # compute usage_type

        # compute order

        # Log the TRX using FUNC
        self._log_transaction(
            amount=amount,
            transaction_type=ReferralWalletTransaction.TransactionType.DEDUCTION,
            description=description,
            bonus_usage_type=usage_type,
            order=order,
        )

    @property
    def total_earned(self):
        return self.available_balance + self.pending_balance + self.total_used

    @property
    def current_balance(self):
        return self.available_balance + self.pending_balance

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

    bonus_usage_type = models.CharField(max_length=20, choices=BonusUsageType.choices, null=True)

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
