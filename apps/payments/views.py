import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer

from .models import Payment
from .serializers import (
    InitializeTransactionSerializer,
    VerifyPaymentSerializer,
)
from .services import PaymentService

payment_service = PaymentService(secret_key=settings.PAYSTACK_SECRET_KEY)

logger = logging.getLogger(__name__)


class InitializeTransactionView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["post"]

    def post(self, request):
        serializer = InitializeTransactionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        order_id = serializer.validated_data["order"]
        try:
            order = Order.objects.get(id=order_id, buyer=request.user)
        except Order.DoesNotExist as e:
            logger.warning(f"Order.DoesNotExist: {e}")
            return Response(
                {"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if order.payment_status == Order.PaymentStatus.PAID:
            return Response(
                {"detail": "Order has already been paid for."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # TODO: Modify this to account for the shipping costs as well.
        amount = order.total_price
        # Convert to kobo (Paystack expects amounts in kobo)
        amount_in_kobo = int(amount * 100)

        try:
            # Initialize payment transaction
            response = payment_service.initialize_transaction(
                email=request.user.email,
                amount=amount_in_kobo,
                currency="NGN",
            )
            Payment.objects.create(
                user=request.user,
                order=order,
                amount=amount,
                currency="NGN",
                ref=response.get("data", {}).get("reference"),
            )
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                f"Exception in InitializeTransactionView.post: {e}", exc_info=True
            )
            return Response(
                {
                    "detail": "Unable to initialize payment. Please try again later or contact support if the issue persists."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

    def get(self, request, reference):
        data = {"reference": reference}
        serializer = VerifyPaymentSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            response = payment_service.verify_payment(reference)
            transaction = Payment.objects.get(ref=reference, user=request.user)

            if response.get("status", False):
                order_obj = transaction.order
                order_obj.payment_status = Order.PaymentStatus.PAID
                transaction.verified = True
                transaction.save()
                order_obj.save(update_fields=["payment_status"])

            data = response.get("data", {})
            if response.get("status", False):
                order = OrderSerializer(transaction.order).data
                return Response(
                    {
                        "status": response.get("status", False),
                        "detail": response.get("message"),
                        "transaction": {
                            "reference": data.get("reference"),
                            "status": data.get("status"),
                            "amount": data.get("amount"),
                            "currency": data.get("currency"),
                            "paid_at": data.get("paid_at"),
                            "channel": data.get("channel"),
                            "gateway_response": data.get("gateway_response"),
                            "order": order,
                        },
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "status": response.get("status", False),
                        "detail": response.get("message"),
                        "order": transaction.order.id,
                    },
                    status=status.HTTP_200_OK,
                )
        except Exception as e:
            logger.error(f"Exception in VerifyPaymentView.get: {e}", exc_info=True)
            return Response(
                {
                    "detail": "Unable to verify payment at this time. Please try again later or contact support if the issue persists."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class WebhookView(APIView):
    http_method_names = ["post"]

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        if not self._is_valid_ip(request):
            return JsonResponse({"detail": "Forbidden: Invalid IP."}, status=403)
        if not self._is_valid_signature(request):
            return JsonResponse({"detail": "Invalid signature."}, status=400)
        event = self._parse_event(request)
        if event is None:
            return JsonResponse({"detail": "Invalid payload."}, status=400)
        result = self._handle_event(event)
        return result or HttpResponse(status=200)

    def _is_valid_ip(self, request):
        ip = request.META.get("REMOTE_ADDR")
        logger.info(f"Webhook request from IP: {ip}")
        return ip in settings.IP_WHITELIST

    def _is_valid_signature(self, request):
        paystack_signature = request.META.get("HTTP_X_PAYSTACK_SIGNATURE")
        secret = settings.PAYSTACK_SECRET_KEY.encode("utf-8")
        body = request.body
        computed_signature = hmac.new(secret, body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(computed_signature, paystack_signature or "")

    def _parse_event(self, request):
        try:
            return (
                request.data
                if isinstance(request.data, dict)
                else json.loads(request.body)
            )
        except Exception as e:
            logger.error(f"Exception in WebhookView._parse_event: {e}", exc_info=True)
            return None

    def _handle_event(self, event):
        event_type = event.get("event")
        data = event.get("data", {})
        reference = data.get("reference")
        if not reference:
            return JsonResponse(
                {"detail": "Missing transaction reference."}, status=400
            )
        if event_type == "charge.success":
            try:
                payment = Payment.objects.get(ref=reference)
                payment.verified = True
                payment.save()

                # Mark the order as paid
                order_instance = payment.order
                if not order_instance.payment_status == Order.PaymentStatus.PAID:
                    order_instance.payment_status = Order.PaymentStatus.PAID
                    order_instance.save(update_fields=["payment_status"])
            except Payment.DoesNotExist as e:
                logger.warning(
                    f"Payment.DoesNotExist in WebhookView._handle_event: {e}"
                )
                return JsonResponse({"detail": "Transaction not found."}, status=404)
            except Exception as e:
                logger.error(f"Error handling charge.success event: {e}", exc_info=True)
                return JsonResponse(
                    {"detail": "Error handling charge.success event."}, status=400
                )
        return None
