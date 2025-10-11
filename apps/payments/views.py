import hashlib
import hmac
import json
import logging
from decimal import Decimal

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




from .models import Escrow, EscrowStatus, Payment, PaymentStatus, PayoutRequest
from .serializers import (
    InitializeTransactionSerializer,
    PriorityWithdrawalSerializer,
    VerifyPaymentSerializer,
    ResolveBankAccountSerializer,
    PayoutRequestSerializer
)
from .services import payment_service
from .utils import distribute_payment_to_vendors

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
        payment = getattr(order, "payments", None)
        payment = payment.first() if payment else None
        if payment and payment.payment_status == PaymentStatus.PAID:
            return Response(
                {"detail": "Order has already been paid for."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # TODO: Modify this to account for the shipping costs as well.
        amount = order.total_price
        # Convert to kobo (Paystack expects amounts in kobo)
        amount_in_kobo = int(round(float(amount) * 100))
        if amount_in_kobo <= 0:
            logger.error("Amount to initialize transaction must be greater than zero.")
            return Response(
                {"detail": "Invalid order amount."}, status=status.HTTP_400_BAD_REQUEST
            )

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
                payment_status=PaymentStatus.PENDING,
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

            data = response.get("data", {})

            # Only mark as PAID if the transaction status is 'success'
            if response.get("status", False) and data.get("status") == "success":
                transaction.payment_status = PaymentStatus.PAID
                transaction.verified = True
                transaction.save(update_fields=["payment_status", "verified"])
                # Create an escrow record to hold funds until release
                try:
                    if transaction.order is not None:
                        # create escrow if not exists
                        Escrow.objects.get_or_create(
                            payment=transaction,
                            order=transaction.order,
                            defaults={
                                "amount": transaction.amount,
                                "currency": transaction.currency,
                                "status": EscrowStatus.HELD,
                            },
                        )
                except Exception as e:
                    logger.error(f"Error creating escrow record: {e}", exc_info=True)
                # remove items with the order products from user's cart
                user = request.user
                order = transaction.order
                user.cart.items.filter(
                    product__in=order.items.values_list("product", flat=True)
                ).delete()

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

                # Mark the payment as paid
                if payment.payment_status != PaymentStatus.PAID:
                    payment.payment_status = PaymentStatus.PAID
                    payment.save(update_fields=["payment_status"])
                    # Create an escrow record to hold funds until release
                    try:
                        if payment.order is not None:
                            Escrow.objects.get_or_create(
                                payment=payment,
                                order=payment.order,
                                defaults={
                                    "amount": payment.amount,
                                    "currency": payment.currency,
                                    "status": EscrowStatus.HELD,
                                },
                            )
                    except Exception as e:
                        logger.error(
                            f"Error creating escrow record in webhook: {e}",
                            exc_info=True,
                        )
                    except Exception as e:
                        logger.error(
                            f"Error crediting vendor wallets in webhook: {e}",
                            exc_info=True,
                        )
                    # remove items with the order products from user's cart
                    user = payment.user
                    order = payment.order
                    user.cart.items.filter(
                        product__in=order.items.values_list("product", flat=True)
                    ).delete()
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


class PriorityWithdrawalView(APIView):
    """Endpoint to request an immediate (priority) payout with a processing fee.

    Request body:
      - amount: Decimal
      - currency: optional (defaults to NGN)

    Response contains the requested amount, fee applied, and net amount to be paid.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["post"]

    # flat fee for priority withdrawals (defaults to 500.00 NGN)
    FEE_FLAT = Decimal(getattr(settings, "PRIORITY_WITHDRAWAL_FEE_FLAT", 500.00))
    MIN_WITHDRAWAL_AMOUNT = Decimal(getattr(settings, "DAILY_PAYOUT_MIN", 5000.00))

    def post(self, request):
        print("Request data:", request.data)
        serializer = PriorityWithdrawalSerializer(data=request.data)
        print("Serializer valid:", serializer.is_valid())
        print("Serializer errors:", serializer.errors)
        print("Validated data:", serializer.validated_data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount = serializer.validated_data["amount"]
        currency = serializer.validated_data.get("currency", "NGN")
        
        if amount is None:
            return Response(
                {"detail": "Amount is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Ensure amount is Decimal
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        wallet = request.user.vendor_wallet
        balance = wallet.balance
        
        print(f"DEBUG: amount={amount}, type={type(amount)}, balance={balance}, type={type(balance)}")
        
        if amount <= 0:
            return Response(
                {"detail": "Withdrawal amount must be greater than zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if amount < self.MIN_WITHDRAWAL_AMOUNT:
            return Response(
                {
                    "detail": f"Minimum withdrawal amount is {self.MIN_WITHDRAWAL_AMOUNT} NGN."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        if amount > balance:
            return Response(
                {"detail": "Insufficient wallet balance."},
                status=status.HTTP_400_BAD_REQUEST,
            )
           
        # detect partial withdrawal 
        is_partial = amount < balance
        # apply flat fee
        fee = self.FEE_FLAT
        total_deduction = amount + fee

        if total_deduction > balance:
            return Response(
                {"detail": "Insufficient balance to cover amount and fee."},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        net_amount = amount - fee
        remaining = balance - total_deduction

        # update wallet
        wallet.balance = remaining
        wallet.save(update_fields=["balance"])

        payout = PayoutRequest.objects.create(
            amount=amount,
            currency=currency,
            vendor=request.user,
            status="pending",
            is_priority=True,
            is_partial=is_partial,
            priority_fee=fee,
            net_amount=net_amount,
            remaining_balance=remaining,
        )

        return Response(
            {
                "status": True,
                "detail": "Priority withdrawal requested.",
                "request": {
                    "id": str(payout.id),
                    "amount": float(amount),
                    "currency": currency,
                    "fee": float(fee),
                    "is_partial": is_partial,
                    "net_amount": float(net_amount),
                    "remaining_balance": float(remaining),
                    "status": payout.status,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class EscrowReleaseView(APIView):
    """Admin endpoint to release an escrowed payment to vendors.

    POST body: { "escrow_id": "uuid" }
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["post"]

    def post(self, request):
        # Minimal permission check -- assume staff can release escrow
        if not request.user.is_staff:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        serializer = VerifyPaymentSerializer(data=request.data)
        # reuse simple serializer for a single field 'reference' isn't ideal, create local handling
        escrow_id = request.data.get("escrow_id")
        if not escrow_id:
            return Response(
                {"detail": "escrow_id required."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            escrow = Escrow.objects.get(id=escrow_id)
            if escrow.status != EscrowStatus.HELD:
                return Response(
                    {"detail": "Escrow not held."}, status=status.HTTP_400_BAD_REQUEST
                )
            result = escrow.release()
            return Response(
                {"status": True, "detail": "Escrow released.", "credits": result},
                status=status.HTTP_200_OK,
            )
        except Escrow.DoesNotExist:
            return Response(
                {"detail": "Escrow not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error releasing escrow: {e}", exc_info=True)
            return Response(
                {"detail": "Unable to release escrow."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class EscrowRefundView(APIView):
    """Admin endpoint to mark and process a refund for an escrow.

    POST body: { "escrow_id": "uuid" }
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["post"]

    def post(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        escrow_id = request.data.get("escrow_id")
        if not escrow_id:
            return Response(
                {"detail": "escrow_id required."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            escrow = Escrow.objects.get(id=escrow_id)
            if escrow.status != EscrowStatus.HELD:
                return Response(
                    {"detail": "Escrow cannot be refunded."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            escrow.refund()
            # Note: actual payment gateway refund should be implemented separately
            return Response(
                {"status": True, "detail": "Escrow marked refunded."},
                status=status.HTTP_200_OK,
            )
        except Escrow.DoesNotExist:
            return Response(
                {"detail": "Escrow not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error refunding escrow: {e}", exc_info=True)
            return Response(
                {"detail": "Unable to refund escrow."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ResolveBankAccountView(APIView):
    """Resolve a bank account number to an account name using the payment service.

    Request body:
      - account_number: str
      - bank_code: str

    Response mirrors the payment provider's response.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["post"]

    def post(self, request):
        serializer = ResolveBankAccountSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        account_number = serializer.validated_data["account_number"]
        bank_code = serializer.validated_data["bank_code"]
        try:
            response = payment_service.resolve_bank_account(account_number, bank_code)
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error resolving bank account: {e}", exc_info=True)
            return Response(
                {"detail": "Unable to resolve account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
