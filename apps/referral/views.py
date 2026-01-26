from rest_framework.generics import ListAPIView
import logging
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from apps.referral.serializers import (
    ReferralWalletSummarySerializer,
    ReferralWalletTransactionSerializer,
)
from common.utils.responses import error_response, success_response
from rest_framework import status

logger = logging.getLogger(__name__)


class WalletHistoryPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 50


class ReferralWalletHistoryView(ListAPIView):
    """Lists the wallet history for the user"""

    serializer_class = ReferralWalletTransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = WalletHistoryPagination

    def get_queryset(self):
        self.request.user
        return self.request.user.referral_wallet.transactions.select_related(
            "order", "referred_user"
        )


class ReferralWalletSummaryView(APIView):
    """
    Return referral wallet summary: total_earned, total_used,
    available
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            wallet = request.user.referral_wallet

            transactions = wallet.transactions.all()

            # totals = transactions.values("transaction_type").annotate(
            #     total=Sum("amount")
            # )
            total_earned = wallet.total_earned

            current_balance = wallet.current_balance
            available_balance = wallet.available_balance
            product_bonus_balance = wallet.product_bonus_balance
            service_bonus_balance = wallet.service_bonus_balance
            pending_balance = wallet.pending_balance

            total_used = wallet.total_used

            last_transaction = transactions.first()

            serializer = ReferralWalletSummarySerializer(
                {
                    "available_balance": available_balance,
                    "product_bonus_balance": product_bonus_balance,
                    "service_bonus_balance": service_bonus_balance,
                    "current_balance": current_balance,
                    "pending_balance": pending_balance,
                    "total_earned": total_earned,
                    "total_used": total_used,
                    "last_transaction_at": last_transaction.created_at
                    if last_transaction
                    else None,
                }
            )
            return success_response(
                data=serializer.data, message="Referral Wallet Summary"
            )

        except Exception as e:
            logger.error(f"Error while fetching wallet summary: {e}")
            return error_response(
                message=f"An error occurred while fetching wallet summary {e}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
