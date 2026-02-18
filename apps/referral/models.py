import uuid
from decimal import Decimal
from django.db import models, transaction
from django.db.models import F
from django.conf import settings
from django.utils import timezone
import secrets
import string
from django.conf import settings

class ReferralProfile(models.Model):
    """
    Extensions to the CustomUser to handle referral codes and status.
    """
    # Define the types clearly
    class ReferralType(models.TextChoices):
        NORMAL = 'normal', 'Normal User'
        INFLUENCER = 'influencer', 'Influencer'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to your CustomUser
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_profile",
    )

    # The code this user shares
    referral_code = models.CharField(
        max_length=20, 
        unique=True, 
        db_index=True
    )

    # Who referred this user?
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referees"
    )

    # The requirement: Track Influencer vs Normal
    referral_type = models.CharField(
        max_length=20, 
        choices=ReferralType.choices, 
        default=ReferralType.NORMAL
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-generate code if not present
        if not self.referral_code:
            self.referral_code = self._generate_unique_code()
        super().save(*args, **kwargs)

    def _generate_unique_code(self):
        """Generate a random 8-char code and ensure it's unique."""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(chars) for _ in range(8))
            # Check if this code already exists in DB to avoid crash
            if not ReferralProfile.objects.filter(referral_code=code).exists():
                return code

    def get_referral_reward_amount(self):
        """
        Centralized logic for how much this user earns per referral.
        This makes changing prices later very easy.
        """
        if self.referral_type == self.ReferralType.INFLUENCER:
            return 1000  # Influencers get 1000 (Example)
        return 300       # Normal users get 300 (Requirement)

    def __str__(self):
        return f"{self.user.email} [{self.referral_type}]"


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

    # add available bonus type balance here, in which
    # the addition of both bonus_type is equal the main available bal
    product_bonus_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    service_bonus_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

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
        self,
        amount: Decimal,
        bonus_usage_type: str,
        description: str = "",
        referred_user: str | None = None,
    ):
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if amount > self.pending_balance:
            raise ValueError("Insufficient pending referral balance")

        if bonus_usage_type not in ReferralWalletTransaction.BonusUsageType.values:
            raise ValueError("Invalid bonus usage type")

        BONUS_FIELD_MAP = {
            ReferralWalletTransaction.BonusUsageType.PRODUCT: "product_bonus_balance",
            ReferralWalletTransaction.BonusUsageType.SERVICE: "service_bonus_balance",
        }
        bonus_field = BONUS_FIELD_MAP[bonus_usage_type]

        self.__class__.objects.filter(pk=self.pk).update(
            available_balance=F("available_balance") + amount,
            pending_balance=F("pending_balance") - amount,
            **{bonus_field: F(bonus_field) + amount},
        )

        self.refresh_from_db(
            fields=["available_balance", "pending_balance", bonus_field]
        )

        # Invariant safety check - optional tho but for more safety
        if self.available_balance != (
            self.product_bonus_balance + self.service_bonus_balance
        ):
            raise RuntimeError("Wallet balance invariant violated")

        # Log the TRX using FUNC
        self._log_transaction(
            amount=amount,
            transaction_type=ReferralWalletTransaction.TransactionType.ADDITION,
            description=description,
            referred_user=referred_user,
            bonus_usage_type=bonus_usage_type,
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
        self, amount: Decimal, bonus_usage_type: str, description: str = "", order=None
    ):
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if amount > self.available_balance:
            raise ValueError("Insufficient referall balance")

        if bonus_usage_type not in ReferralWalletTransaction.BonusUsageType.values:
            raise ValueError("Invalid bonus usage type")

        BONUS_FIELD_MAP = {
            ReferralWalletTransaction.BonusUsageType.PRODUCT: "product_bonus_balance",
            ReferralWalletTransaction.BonusUsageType.SERVICE: "service_bonus_balance",
        }
        bonus_field = BONUS_FIELD_MAP[bonus_usage_type]

        print(bonus_field, "bonus field")

        self.__class__.objects.filter(pk=self.pk).update(
            available_balance=F("available_balance") - amount,
            total_used=F("total_used") + amount,
            **{bonus_field: F(bonus_field) - amount},
        )

        self.refresh_from_db(fields=["available_balance", "total_used", bonus_field])

        # Log the TRX using FUNC
        self._log_transaction(
            amount=amount,
            transaction_type=ReferralWalletTransaction.TransactionType.DEDUCTION,
            description=description,
            bonus_usage_type=bonus_usage_type,
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

    bonus_usage_type = models.CharField(
        max_length=20, choices=BonusUsageType.choices, null=True
    )

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

