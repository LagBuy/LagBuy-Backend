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

        self.wallet.add_pending_bonus(Decimal("500.00"), description="Pending referral")

        self.wallet.add_available_bonus(
            Decimal("300.00"),
            description="Referral Bonus - Verification",
            bonus_usage_type=ReferralWalletTransaction.BonusUsageType.PRODUCT,
        )

        self.wallet.add_available_bonus(
            Decimal("200.00"),
            description="Referral Bonus - first product purchase done",
            bonus_usage_type=ReferralWalletTransaction.BonusUsageType.SERVICE,
        )

    def test_add_pending_bonus(self):
        """Tests the add_pending_bonus method on the ref_wallet"""
        self.wallet.add_pending_bonus(Decimal("500.00"), description="Pending referral")

        self.assertEqual(self.wallet.pending_balance, Decimal("500.00"))

    def test_add_available_bonus(self):
        """
        Tests the add_available_bonus method adds the correct bonuses
        """

        self.assertEqual(self.wallet.available_balance, Decimal("500.00"))
        self.assertEqual(self.wallet.product_bonus_balance, Decimal("300.00"))
        self.assertEqual(self.wallet.service_bonus_balance, Decimal("200.00"))

        self.assertEqual(self.wallet.pending_balance, Decimal("0.00"))

    def test_add_available_bonus_fail_insufficient_pending_bonus(self):
        """
        Tests the add-available_bonus method on the ref_wallet throws an error against insufficient pending_bal
        """

        with self.assertRaises(ValueError):
            self.wallet.add_available_bonus(
                Decimal("1000.00"),
                description="Referral Bonus",
                bonus_usage_type=ReferralWalletTransaction.BonusUsageType.SERVICE,
            )

    def test_deduct_balance_success(self):
        """
        Tests the deduct method removes the correct bonuses
        """
        current_product_balance = self.wallet.product_bonus_balance
        current_service_balance = self.wallet.service_bonus_balance

        self.wallet.deduct(
            amount=Decimal("150.00"),
            description="Order payment",
            bonus_usage_type=ReferralWalletTransaction.BonusUsageType.PRODUCT,
        )

        self.wallet.deduct(
            amount=Decimal("200.00"),
            description="Services payment",
            bonus_usage_type=ReferralWalletTransaction.BonusUsageType.SERVICE,
        )

        self.assertEqual(self.wallet.available_balance, Decimal("150.00"))
        self.assertEqual(self.wallet.product_bonus_balance, Decimal("150.00"))

        self.assertNotEqual(current_product_balance, self.wallet.product_bonus_balance)
        self.assertNotEqual(current_service_balance, self.wallet.service_bonus_balance)

        self.assertEqual(self.wallet.total_used, Decimal("350.00"))

    def test_deduct_balance_insufficient_funds(self):
        """Tests the deduct_bal method on the ref_wallet throws an error against insufficient funds"""

        with self.assertRaises(ValueError):
            self.wallet.deduct(
                amount=Decimal("1000.00"),
                description="Invalid deduction",
                bonus_usage_type=ReferralWalletTransaction.BonusUsageType.PRODUCT,
            )

    def test_balance_computation_helpers(self):
        """Tests the summary computation helpers"""
        self.wallet.deduct(
            amount=Decimal("200.00"),
            description="Order payment",
            bonus_usage_type=ReferralWalletTransaction.BonusUsageType.SERVICE,
        )

        self.assertEqual(self.wallet.total_earned, Decimal("500.00"))
        self.assertEqual(self.wallet.current_balance, Decimal("300.00"))


class ReferralWalletSummaryTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="user@test.com", password="password123"
        )
        self.client = APIClient()

        self.client.force_authenticate(user=self.user)

        self.wallet = self.user.referral_wallet

        self.wallet.add_pending_bonus(
            amount=Decimal("1000.00"),
            description="Pending referral",
        )
        self.wallet.add_available_bonus(
            Decimal("300.00"),
            description="Referral Bonus - Verification complete",
            bonus_usage_type=ReferralWalletTransaction.BonusUsageType.PRODUCT,
        )

        self.wallet.add_available_bonus(
            Decimal("200.00"),
            description="Referral Bonus - first product purchase done",
            bonus_usage_type=ReferralWalletTransaction.BonusUsageType.SERVICE,
        )
        self.wallet.deduct(
            amount=Decimal("200.00"),
            description="Used bonus",
            bonus_usage_type=ReferralWalletTransaction.BonusUsageType.PRODUCT,
        )

        self.url = reverse("referral-wallet-summary")

    def test_get_wallet_summary_success(self):
        """Tests the get ref_wallet summary endpoint"""
        response = self.client.get(self.url)
        print(self.url)
        print(response.data)

        data = response.data["data"]

        # self.assertEqual(response.status_code, 200)
        self.assertEqual(data["current_balance"], "800.00")
        self.assertEqual(data["available_balance"], "300.00")
        self.assertEqual(data["product_bonus_balance"], "100.00")
        self.assertEqual(data["service_bonus_balance"], "200.00")
        self.assertEqual(data["pending_balance"], "500.00")
        self.assertEqual(data["total_earned"], "1000.00")
        self.assertEqual(data["total_used"], "200.00")
        self.assertIsNotNone(data["last_transaction_at"])

        # self.assertEqual(data["currency"], "NGN")

    def test_wallet_summary_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)


class ReferralWalletTransactionsTest(TestCase):
    def setUp(self) -> None:
        self.user = CustomUser.objects.create_user(
            email="ops@test.com", password="password123"
        )
        self.client = APIClient()

        self.client.force_authenticate(user=self.user)
        self.wallet = self.user.referral_wallet

        self.wallet.add_pending_bonus(
            Decimal("500.00"),
            description="Pending referral",
        )

    def test_add_available_bonus_creates_transaction(self):
        self.wallet.add_available_bonus(
            Decimal("300.00"),
            description="Referral Bonus - Verification done",
            bonus_usage_type=ReferralWalletTransaction.BonusUsageType.PRODUCT,
        )

        trx = ReferralWalletTransaction.objects.get(
            wallet=self.wallet,
            transaction_type=ReferralWalletTransaction.TransactionType.ADDITION,
        )

        self.assertEqual(trx.amount, Decimal("300.00"))
        self.assertEqual(
            trx.transaction_type, ReferralWalletTransaction.TransactionType.ADDITION
        )
        self.assertEqual(trx.description, "Referral Bonus - Verification done")
        self.assertEqual(self.wallet.available_balance, Decimal("300.00"))
        self.assertEqual(self.wallet.product_bonus_balance, Decimal("300.00"))
        self.assertEqual(self.wallet.pending_balance, Decimal("200.00"))

    def test_add_pending_bonus_creates_pending_transaction(self):
        trx = ReferralWalletTransaction.objects.get(wallet=self.wallet)

        self.assertEqual(trx.amount, Decimal("500.00"))
        self.assertEqual(
            trx.transaction_type, ReferralWalletTransaction.TransactionType.PENDING
        )
        self.assertEqual(trx.description, "Pending referral")

    def test_deduction_creates_transaction_with_order(self):
        order = Order.objects.create(
            buyer=self.user,
            delivery_address="Test address",
        )

        self.wallet.add_available_bonus(
            Decimal("300.00"),
            description="Referral Bonus - Verification done",
            bonus_usage_type=ReferralWalletTransaction.BonusUsageType.PRODUCT,
        )

        self.wallet.deduct(
            amount=Decimal("150.00"),
            description="Order payment",
            order=order,
            bonus_usage_type=ReferralWalletTransaction.BonusUsageType.PRODUCT,
        )

        trx = ReferralWalletTransaction.objects.filter(
            transaction_type=ReferralWalletTransaction.TransactionType.DEDUCTION
        ).get()
        # print(trx)
        self.assertEqual(trx.order, order)
        self.assertEqual(trx.amount, Decimal("150.00"))

    def test_wallet_trx_history_is_paginated(self):
        for i in range(25):
            self.wallet.add_available_bonus(
                Decimal("10.00"),
                description="Referral Bonus",
                bonus_usage_type=ReferralWalletTransaction.BonusUsageType.PRODUCT,
            )

        url = reverse("referral-wallet-history")
        print(url)
        response = self.client.get(url)

        # print(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 20)
