import logging
from typing import Any, Dict

import requests
from django.conf import settings


class PaymentService:
    BASE_URL = settings.PAYSTACK_BASE_URL
    HEADERS = {"Content-Type": "application/json"}

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.headers = {**self.HEADERS, "Authorization": f"Bearer {self.secret_key}"}

    def _make_request(
        self, method: str, endpoint: str, data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.request(method, url, headers=self.headers, json=data)
        if response.status_code != 200:
            logging.error(
                f"Request to {url} failed with status code {response.status_code}: {response.text}"
            )
            response.raise_for_status()
        return response.json()

    def list_banks(self, country: str = "nigeria", **kwargs) -> Dict[str, Any]:
        allowed_kwargs = {"use_cursor", "perPage", "next", "previous"}
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_kwargs}
        return self._make_request("GET", f"/bank?country={country}", filtered_kwargs)

    def resolve_account_number(
        self, account_number: str, bank_code: str
    ) -> Dict[str, Any]:
        return self._make_request(
            "GET",
            f"/bank/resolve?account_number={account_number}&bank_code={bank_code}",
        )

    def initialize_transaction(
        self, email: str, amount: int, currency: str = "NGN", **kwargs
    ) -> Dict[str, Any]:
        allowed_kwargs = {
            "callback_url",
            "reference",
            "plan",
            "subaccount",
            "transaction_charge",
            "channels",
            "split_code",
            "bearer",
            "metadata",
        }
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_kwargs}
        data = {
            "email": email,
            "amount": amount,
            "currency": currency,
            **filtered_kwargs,
        }
        return self._make_request("POST", "/transaction/initialize", data)

    def verify_payment(self, reference: str) -> Dict[str, Any]:
        return self._make_request("GET", f"/transaction/verify/{reference}")

    def create_refund(
        self, transaction_id: str, amount: int, **kwargs
    ) -> Dict[str, Any]:
        allowed_kwargs = {"currency", "customer_note", "merchant_note"}
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_kwargs}
        data = {"transaction": transaction_id, "amount": amount, **filtered_kwargs}
        return self._make_request("POST", "/refund", data)

    def create_transfer_recipient(
        self,
        name: str,
        account_number: str,
        bank_code: str,
        type: str = "nuban",
        currency: str = "NGN",
    ) -> dict:
        data = {
            "type": type,
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": currency,
        }
        return self._make_request("POST", "/transferrecipient", data)

    def initiate_transfer(
        self, recipient: str, amount: int, reason: str, currency: str = "NGN"
    ) -> dict:
        data = {
            "source": "balance",
            "amount": amount,
            "recipient": recipient,
            "currency": currency,
            "reason": reason,
        }
        return self._make_request("POST", "/transfer", data)

    def finalize_transfer(self, transfer_code: str, otp: str) -> dict:
        data = {"transfer_code": transfer_code, "otp": otp}
        return self._make_request("POST", "/transfer/finalize_transfer", data)

    def verify_transfer(self, reference: str) -> dict:
        """Verify a transfer using the transfer reference."""
        return self._make_request("GET", f"/transfer/verify/{reference}")

    def handle_error(self, response: Dict[str, Any]):
        """Raise an exception if the response indicates an error."""
        if not response.get("status"):
            raise Exception(response.get("message"))
