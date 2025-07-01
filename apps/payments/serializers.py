from rest_framework import serializers


class InitializeTransactionSerializer(serializers.Serializer):
    order = serializers.UUIDField()


class VerifyPaymentSerializer(serializers.Serializer):
    reference = serializers.CharField(required=True)


class CreateRefundSerializer(serializers.Serializer):
    transaction_id = serializers.CharField()
