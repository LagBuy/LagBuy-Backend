from rest_framework import serializers
from apps.payments.models import PayoutRequest


class InitializeTransactionSerializer(serializers.Serializer):
    order = serializers.UUIDField()


class VerifyPaymentSerializer(serializers.Serializer):
    reference = serializers.CharField(required=True)


class CreateRefundSerializer(serializers.Serializer):
    transaction_id = serializers.CharField()


class PriorityWithdrawalSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField(max_length=5, required=False, default="NGN")


class EscrowSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    order = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField(max_length=5, required=False, default="NGN")
    status = serializers.CharField(read_only=True)


class EscrowActionSerializer(serializers.Serializer):
    escrow_id = serializers.UUIDField()


class ResolveBankAccountSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=20)
    bank_code = serializers.CharField(max_length=20)


class PayoutRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutRequest
        fields = ["id", "amount", "currency", "status", "requested_at"]

    def validate_amount(self, value):
        request = self.context.get("request")
        user = request.user
        # Get vendor wallet balance (depends where it's stored)
        wallet = user.vendor_profile.wallet  

        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        if value > wallet.balance:
            raise serializers.ValidationError("Insufficient wallet balance.")
        return value
    