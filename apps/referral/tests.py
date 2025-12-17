from django.test import TestCase
# from django.contrib.auth import get_user_model
from apps.referral.models import ReferralWallet
from apps.userAuth.models import CustomUser


# User = get_user_model()


class ReferralWalletCreationTest(TestCase):
    def test_wallet_is_created_on_user_creation(self):
        user = CustomUser.objects.create_user(
            email="wallet@test.com",
            password="password123",
        )

        self.assertTrue(
            ReferralWallet.objects.filter(user=user).exists(),
            "Referral wallet should be created automatically for a new user",
        )

    def test_wallet_is_created_only_once(self):
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
