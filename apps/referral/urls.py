from django.urls import path
from drf_spectacular.utils import extend_schema_view, extend_schema

from .views import ReferralWalletHistoryView

urlpatterns = [
    path("", ReferralWalletHistoryView.as_view(), name="referral-wallet-history"),
]
