import uuid
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.cart.models import Cart, CartItem
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment, PaymentStatus, PayoutRequest
from apps.products.models import Product
from apps.profiles.models import UsersProfile, VendorsProfile
from apps.userAuth.models import CustomUser

User = get_user_model()


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class InitializeTransactionViewTestCase(APITestCase):
    """Test cases for InitializeTransactionView"""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        UsersProfile.objects.create(user=self.user, first_name="Test", last_name="User")
        self.order = Order.objects.create(
            buyer=self.user, delivery_address="123 Test Street"
        )
        self.url = reverse("initialize_transaction")

    def test_initialize_transaction_unauthenticated(self):
        """Test that unauthenticated users cannot initialize transactions"""
        data = {"order": str(self.order.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_initialize_transaction_invalid_order_id(self):
        """Test initialization with invalid order ID"""
        self.client.force_authenticate(user=self.user)
        data = {"order": "invalid-uuid"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_initialize_transaction_order_not_found(self):
        """Test initialization with non-existent order"""
        self.client.force_authenticate(user=self.user)
        fake_uuid = str(uuid.uuid4())
        data = {"order": fake_uuid}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_initialize_transaction_order_not_owned(self):
        """Test initialization with order not owned by user"""
        other_user = CustomUser.objects.create_user(
            email="other@example.com", password="testpass123"
        )
        other_order = Order.objects.create(
            buyer=other_user, delivery_address="456 Other Street"
        )

        self.client.force_authenticate(user=self.user)
        data = {"order": str(other_order.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_initialize_transaction_already_paid(self):
        """Test initialization for already paid order"""
        payment = Payment.objects.create(
            user=self.user,
            order=self.order,
            amount=self.order.total_price,
            currency="NGN",
            ref="test_ref_already_paid",
            payment_status=PaymentStatus.PAID,
        )
        self.client.force_authenticate(user=self.user)
        data = {"order": str(self.order.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.payments.views.payment_service.initialize_transaction")
    def test_initialize_transaction_success(self, mock_initialize):
        """Test successful transaction initialization"""
        # Mock the payment service response
        mock_response = {
            "status": True,
            "data": {
                "reference": "test_ref_123",
                "authorization_url": "https://checkout.paystack.com/test_ref_123",
            },
        }
        mock_initialize.return_value = mock_response

        # Mock order total_price property
        with patch.object(Order, "total_price", new_callable=lambda: Decimal("100.00")):
            self.client.force_authenticate(user=self.user)
            data = {"order": str(self.order.id)}
            response = self.client.post(self.url, data)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, mock_response)

            # Verify payment object was created
            payment = Payment.objects.get(ref="test_ref_123")
            self.assertEqual(payment.user, self.user)
            self.assertEqual(payment.order, self.order)
            self.assertEqual(payment.amount, Decimal("100.00"))

            # Verify amount was converted to kobo
            mock_initialize.assert_called_once_with(
                email=self.user.email,
                amount=10000,
                currency="NGN",
            )

    @patch("apps.payments.views.payment_service.initialize_transaction")
    def test_initialize_transaction_service_error(self, mock_initialize):
        """Test transaction initialization with service error"""
        mock_initialize.side_effect = Exception("Service error")

        with patch.object(Order, "total_price", new_callable=lambda: Decimal("100.00")):
            self.client.force_authenticate(user=self.user)
            data = {"order": str(self.order.id)}
            response = self.client.post(self.url, data)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("Unable to initialize payment", response.data["detail"])


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class VerifyPaymentViewTestCase(APITestCase):
    """Test cases for VerifyPaymentView"""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.order = Order.objects.create(
            buyer=self.user, delivery_address="123 Test Street"
        )
        self.payment = Payment.objects.create(
            user=self.user,
            order=self.order,
            amount=Decimal("100.00"),
            ref="test_ref_123",
            currency="NGN",
            payment_status=PaymentStatus.PENDING,
        )
        self.product = Product.objects.create(
            name="Test Product",
            price=100.0,
            description="Test Description",
            stock_quantity=10,
            seller=self.user,
        )
        self.order_item = OrderItem.objects.create(
            order=self.order, product=self.product, quantity=2
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart, product=self.product, quantity=2
        )

    def test_verify_payment_unauthenticated(self):
        """Test that unauthenticated users cannot verify payments"""
        url = reverse("verify_payment", kwargs={"reference": self.payment.ref})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("apps.payments.views.payment_service.verify_payment")
    def test_verify_payment_success(self, mock_verify):
        """Test successful payment verification"""
        mock_response = {
            "status": True,
            "message": "Verification successful",
            "data": {
                "reference": "test_ref_123",
                "status": "success",
                "amount": 10000,
                "currency": "NGN",
                "paid_at": "2023-01-01T12:00:00Z",
                "channel": "card",
                "gateway_response": "Successful",
            },
        }
        mock_verify.return_value = mock_response

        self.client.force_authenticate(user=self.user)
        url = reverse("verify_payment", kwargs={"reference": self.payment.ref})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["status"])
        self.assertIn("transaction", response.data)
        self.assertIn("order", response.data["transaction"])

        # Verify payment and order were updated
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertTrue(self.payment.verified)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)
        # test the item was removed from cart
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.items.count(), 0)

    @patch("apps.payments.views.payment_service.verify_payment")
    def test_verify_payment_failed(self, mock_verify):
        """Test failed payment verification"""
        mock_response = {
            "status": False,
            "message": "Payment failed",
            "data": {"reference": "test_ref_123", "status": "failed"},
        }
        mock_verify.return_value = mock_response

        self.client.force_authenticate(user=self.user)
        url = reverse("verify_payment", kwargs={"reference": self.payment.ref})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["status"])

        # Verify payment and order were not updated
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertFalse(self.payment.verified)
        # If payment exists and is pending, expect 'pending'
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.UNPAID)

    def test_verify_payment_not_found(self):
        """Test verification with non-existent payment reference"""
        self.client.force_authenticate(user=self.user)
        url = reverse("verify_payment", kwargs={"reference": "non_existent_ref"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.payments.views.payment_service.verify_payment")
    def test_verify_payment_service_error(self, mock_verify):
        """Test payment verification with service error"""
        mock_verify.side_effect = Exception("Service error")

        self.client.force_authenticate(user=self.user)
        url = reverse("verify_payment", kwargs={"reference": self.payment.ref})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unable to verify payment", response.data["detail"])


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class ProcessPayoutsCommandTestCase(APITestCase):
    """Tests for the process_payouts management command ensuring priority requests are excluded."""

    def setUp(self):
        self.vendor = CustomUser.objects.create_user(
            email="vendor@example.com", password="testpass"
        )
        VendorsProfile.objects.create(
            user=self.vendor, bank_code="044", account_number="1234567890"
        )

    @patch(
        "apps.payments.management.commands.process_payouts.payment_service.create_transfer_recipient"
    )
    @patch(
        "apps.payments.management.commands.process_payouts.payment_service.initiate_transfer"
    )
    def test_command_skips_priority_requests(
        self, mock_initiate, mock_create_recipient
    ):
        # Mock successful gateway responses
        mock_create_recipient.return_value = {
            "status": True,
            "data": {"recipient_code": "RCP_TEST"},
        }
        mock_initiate.return_value = {
            "status": True,
            "data": {"transfer_code": "TRF_TEST"},
        }

        # create one priority and one regular payout
        priority = PayoutRequest.objects.create(
            amount=Decimal("1000.00"),
            currency="NGN",
            vendor=self.vendor,
            is_priority=True,
        )
        regular = PayoutRequest.objects.create(
            amount=Decimal("2000.00"),
            currency="NGN",
            vendor=self.vendor,
            is_priority=False,
        )

        # run management command
        call_command("process_payouts")

        # Refresh from DB
        priority.refresh_from_db()
        regular.refresh_from_db()

        # priority should remain unprocessed and status should still be PENDING
        self.assertIsNone(priority.processed_at)
        self.assertEqual(priority.status, PaymentStatus.PENDING)

        # regular should be processed and marked PAID
        self.assertIsNotNone(regular.processed_at)
        self.assertEqual(regular.status, PaymentStatus.PAID)


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class PriorityWithdrawalEndpointTestCase(APITestCase):
    """Tests for the priority withdrawal endpoint behavior."""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email="vendor2@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("priority_withdraw")

    def test_priority_withdraw_amount_too_small(self):
        data = {"amount": "100.00"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_priority_withdraw_success_creates_request(self):
        data = {"amount": "2000.00", "currency": "NGN"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # verify PayoutRequest created
        pr = PayoutRequest.objects.get(id=response.data["request"]["id"])
        self.assertTrue(pr.is_priority)
        self.assertIsNotNone(pr.priority_fee)
        self.assertIsNotNone(pr.net_amount)
