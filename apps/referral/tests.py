from decimal import Decimal
from django.test import TestCase
from django.urls import reverse

# from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.orders.models import Order
from apps.referral.models import ReferralWallet, ReferralWalletTransaction
from apps.userAuth.models import CustomUser


# User = get_user_model()


class ReferralWalletCreationTest(TestCase):
    def test_wallet_is_created_on_user_creation(self):
        """Tests the create_wallet signal is fired on user creation"""
        user = CustomUser.objects.create_user(
            email="wallet@test.com",
            password="password123",
        )

        self.assertTrue(
            ReferralWallet.objects.filter(user=user).exists(),
            "Referral wallet should be created automatically for a new user",
        )

    def test_wallet_is_created_only_once(self):
        """Tests the create_wallet signal is fired once"""
        user = CustomUser.objects.create_user(
            email="wallet2@test.com",
            password="password123",
        )
        user.save()

        wallets = ReferralWallet.objects.filter(user=user)
        self.assertEqual(
            wallets.count(),
            1,
            "Referral wallet should only be one for each user",
        )


class ReferralWalletOperationsTest(TestCase):
    def setUp(self) -> None:
        self.user = CustomUser.objects.create_user(
            email="ops@test.com", password="password123"
        )
        self.wallet = self.user.referral_wallet

    def test_add_available_bonus(self):
        """Tests the add_available_bonus method on the ref_wallet is working as expected"""
        self.wallet.add_available_bonus(Decimal("500.00"), description="Referral Bonus")

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, Decimal("500.00"))
        self.assertEqual(self.wallet.pending_balance, Decimal("0.00"))

    def test_add_pending_bonus(self):
        """Tests the add_pending_bonus method on the ref_wallet"""
        self.wallet.add_pending_bonus(Decimal("300.00"), description="Pending referral")

        self.wallet.refresh_from_db()

        self.assertEqual(self.wallet.pending_balance, Decimal("300.00"))
        self.assertEqual(self.wallet.available_balance, Decimal("0.00"))

    def test_deduct_balance_success(self):
        """Tests the deduct_bal method on the ref_wallet"""
        self.wallet.add_available_bonus(Decimal("400.00"), description="Referral")

        self.wallet.deduct(
            amount=Decimal("150.00"),
            description="Order payment",
            usage_type=ReferralWalletTransaction.BonusUsageType.PRODUCT,
        )

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, Decimal("250.00"))
        self.assertEqual(self.wallet.total_used, Decimal("150.00"))

    def test_deduct_balance_insufficient_funds(self):
        """Tests the deduct_bal method on the ref_wallet throws an error against insufficient funds"""
        self.wallet.add_available_bonus(
            Decimal("100.00"),
            description="Referral",
        )

        with self.assertRaises(ValueError):
            self.wallet.deduct(
                amount=Decimal("200.00"), description="Invalid deduction"
            )

    def test_balance_computation_helpers(self):
        """Tests the summary computation helpers"""
        self.wallet.add_available_bonus(Decimal("200.00"), "Bonus A")
        self.wallet.add_pending_bonus(Decimal("100.00"), "Bonus B")
        self.wallet.deduct(Decimal("50.00"), "Usage")

        self.wallet.refresh_from_db()

        self.assertEqual(self.wallet.total_earned, Decimal("300.00"))
        self.assertEqual(self.wallet.current_balance, Decimal("250.00"))


class ReferralWalletTransactionsTest(TestCase):
    def setUp(self) -> None:
        self.user = CustomUser.objects.create_user(
            email="ops@test.com", password="password123"
        )
        self.client = APIClient()

        self.client.force_authenticate(user=self.user)
        self.wallet = self.user.referral_wallet

    def test_add_available_bonus_creates_transaction(self):
        self.wallet.add_available_bonus(
            amount=Decimal("500.00"),
            description="Referral bonus",
        )

        trx = ReferralWalletTransaction.objects.get(wallet=self.wallet)

        self.assertEqual(trx.amount, Decimal("500.00"))
        self.assertEqual(
            trx.transaction_type, ReferralWalletTransaction.TransactionType.ADDITION
        )
        self.assertEqual(trx.description, "Referral bonus")

    def test_add_pending_bonus_creates_pending_transaction(self):
        self.wallet.add_pending_bonus(
            amount=Decimal("200.00"),
            description="Pending referral",
        )

        trx = ReferralWalletTransaction.objects.get(wallet=self.wallet)

        self.assertEqual(trx.amount, Decimal("200.00"))
        self.assertEqual(
            trx.transaction_type, ReferralWalletTransaction.TransactionType.PENDING
        )
        self.assertEqual(trx.description, "Pending referral")

    def test_deduction_creates_transaction_with_order(self):
        order = Order.objects.create(
            buyer=self.user,
            delivery_address="Test address",
        )

        self.wallet.add_available_bonus(Decimal("500.00"), "Bonus")

        self.wallet.deduct(
            amount=Decimal("150.00"),
            description="Order payment",
            order=order,
            usage_type=ReferralWalletTransaction.BonusUsageType.PRODUCT,
        )

        trx = ReferralWalletTransaction.objects.filter(
            transaction_type=ReferralWalletTransaction.TransactionType.DEDUCTION
        ).get()
        print(trx)
        self.assertEqual(trx.order, order)
        self.assertEqual(trx.amount, Decimal("150.00"))

    def test_wallet_trx_history_is_paginated(self):
        for i in range(25):
            self.wallet.add_available_bonus(
                Decimal("10.00"),
                description=f"Bonus {i}",
            )

        url = reverse("referral-wallet-history")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 20)
