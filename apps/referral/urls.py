from django.urls import path
from drf_spectacular.utils import extend_schema_view, extend_schema

from .views import ReferralWalletHistoryView, ReferralWalletSummaryView

urlpatterns = [
    path("wallet/history/", ReferralWalletHistoryView.as_view(), name="referral-wallet-history"),
    path("wallet/summary/", ReferralWalletSummaryView.as_view(), name="referral-wallet-summary"),
    
]
