from rest_framework import serializers


class InitializeTransactionSerializer(serializers.Serializer):
    order = serializers.UUIDField()


class VerifyPaymentSerializer(serializers.Serializer):
    reference = serializers.CharField(required=True)


class CreateRefundSerializer(serializers.Serializer):
    transaction_id = serializers.CharField()


class PriorityWithdrawalSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField(max_length=5, required=False, default="NGN")
