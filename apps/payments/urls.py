from django.urls import path

from .views import (
    InitializeTransactionView,
    VerifyPaymentView,
    WebhookView,
)

urlpatterns = [
    path(
        "initialize/",
        InitializeTransactionView.as_view(),
        name="initialize_transaction",
    ),
    path("verify/<str:reference>/", VerifyPaymentView.as_view(), name="verify_payment"),
    path("webhook/", WebhookView.as_view(), name="webhook"),
]
