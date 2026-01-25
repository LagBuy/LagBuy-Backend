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


class ReferralWalletSummarySerializer(serializers.Serializer):
    current_balance = serializers.DecimalField(max_digits=18, decimal_places=2)
    available_balance = serializers.DecimalField(max_digits=18, decimal_places=2)
    product_bonus_balance = serializers.DecimalField(max_digits=18, decimal_places=2)
    service_bonus_balance = serializers.DecimalField(max_digits=18, decimal_places=2)
    pending_balance = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_earned = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_used = serializers.DecimalField(max_digits=18, decimal_places=2)
    last_transaction_at = serializers.DateTimeField(allow_null=True)
