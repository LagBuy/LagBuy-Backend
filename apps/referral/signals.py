from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from apps.referral.models import ReferralWallet

User = get_user_model()

@receiver(post_save, sender=User)
def create_referral_wallet(sender, instance, created, **kwargs):
    """
    Ensure every user has a referral wallet.
    Runs only on user creation.
    """
    if not created:
        return

    ReferralWallet.objects.get_or_create(user=instance)