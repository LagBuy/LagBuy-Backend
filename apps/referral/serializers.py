from rest_framework import serializers

from apps.referral.models import ReferralWalletTransaction


class ReferralWalletTransactionSerializer(serializers.ModelSerializer):
    referred_user_name = serializers.SerializerMethodField()

    class Meta:
        model = ReferralWalletTransaction
        fields = [
            "id",
            "amount",
            "transaction_type",
            "bonus_usage_type",
            "created_at",
            "referred_user_name",
        ]

    def get_referred_user_name(self, obj):
        if obj.referred_user:
            profile = getattr(obj.referred_user, "user_profile", None)
            if profile:
                return f"{profile.first_name} {profile.last_name}"
        return None
