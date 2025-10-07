from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view

from .views import (
    EscrowRefundView,
    EscrowReleaseView,
    InitializeTransactionView,
    PriorityWithdrawalView,
    VerifyPaymentView,
    WebhookView,
    ResolveBankAccountView,
)

InitializeTransactionView = extend_schema_view(
    post=extend_schema(tags=["Payments"], summary="Initialize a payment transaction")
)(InitializeTransactionView)
VerifyPaymentView = extend_schema_view(
    get=extend_schema(tags=["Payments"], summary="Verify a payment transaction")
)(VerifyPaymentView)
WebhookView = extend_schema_view(
    post=extend_schema(tags=["Payments"], summary="Handle payment gateway webhooks")
)(WebhookView)

ResolveBankAccountView = extend_schema_view(
    post=extend_schema(
        tags=["Payments"], summary="Resolve bank account number to account name"
    )
)(ResolveBankAccountView)

EscrowReleaseView = extend_schema_view(
    post=extend_schema(tags=["Payments"], summary="Release escrow to vendors")
)(EscrowReleaseView)

EscrowRefundView = extend_schema_view(
    post=extend_schema(tags=["Payments"], summary="Mark escrow as refunded")
)(EscrowRefundView)

urlpatterns = [
    path(
        "initialize/",
        InitializeTransactionView.as_view(),
        name="initialize_transaction",
    ),
    path("verify/<str:reference>/", VerifyPaymentView.as_view(), name="verify_payment"),
    path("webhook/", WebhookView.as_view(), name="webhook"),
    path(
        "priority-withdraw/",
        PriorityWithdrawalView.as_view(),
        name="priority_withdraw",
    ),
    path("escrow/release/", EscrowReleaseView.as_view(), name="escrow_release"),
    path("escrow/refund/", EscrowRefundView.as_view(), name="escrow_refund"),
    path(
        "resolve-account/",
        ResolveBankAccountView.as_view(),
        name="resolve_bank_account",
    ),
]
