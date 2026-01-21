from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from apps.referral.serializers import ReferralWalletTransactionSerializer


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
