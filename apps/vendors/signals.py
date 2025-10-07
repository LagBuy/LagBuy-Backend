from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.profiles.models import VendorsProfile

from .models import VendorWallet


@receiver(post_save, sender=VendorsProfile)
def ensure_wallet_for_vendor_profile(sender, instance, created, **kwargs):
    """Ensure a VendorWallet exists for every vendor profile."""
    if not instance or not instance.user:
        return
    try:
        VendorWallet.objects.get_or_create(
            vendor=instance.user, defaults={"balance": Decimal("0.00")}
        )
    except Exception:
        # don't raise in signal; log if needed
        pass
