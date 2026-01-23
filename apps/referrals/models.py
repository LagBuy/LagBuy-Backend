from django.db import models
from profiles.models import UsersProfile

# Create your models here.
class Referral(models.Model):
    referrer = models.ForeignKey(UsersProfile, on_delete=models.CASCADE, related_name="sent_referrals")
    referred = models.OneToOneField(UsersProfile, on_delete=models.CASCADE, related_name="referral_record")

    is_verified = models.BooleanField(default=False)
    first_purchase_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
