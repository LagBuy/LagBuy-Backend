from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import Product
from apps.users.models import CustomUser

from .models import Order


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class OrderModelTest(TestCase):
    """Test cases for the Order model."""

    @classmethod
    def setUpTestData(cls):
        cls.buyer = CustomUser.objects.create_user(
            username="buyer",
            password="password",
            email="buyer@example.com",
            first_name="Buyer",
            last_name="User",
            phone_number="1234567890",
        )
        cls.seller = CustomUser.objects.create_user(
            username="seller",
            password="password",
            email="seller@example.com",
            first_name="Seller",
            last_name="User",
            phone_number="0987654321",
        )
        cls.product = Product.objects.create(
            name="Test Product",
            price=100.0,
            images=[],
            description="Test Description",
            stock_quantity=10,
            seller=cls.seller,
        )
        cls.order = Order.objects.create(
            buyer=cls.buyer, seller=cls.seller, delivery_address="123 Test St"
        )
        cls.order.products.add(cls.product)

    def test_order_creation(self):
        """Test that an order is created successfully."""
        self.assertEqual(self.order.buyer, self.buyer)
        self.assertEqual(self.order.seller, self.seller)
        self.assertEqual(self.order.delivery_address, "123 Test St")
        self.assertEqual(self.order.total_price, 100.0)
        self.assertEqual(self.order.delivery_fee, 5.0)
        self.assertIn(self.product, self.order.products.all())

    def test_order_str(self):
        """Test the string representation of the order."""
        self.assertEqual(str(self.order), f"Order - {self.order.id} by {self.buyer}")


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class OrderAPITest(TestCase):
    """Test cases for the Order API views."""

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.buyer = CustomUser.objects.create_user(
            username="buyer",
            password="password",
            email="buyer@example.com",
            first_name="Buyer",
            last_name="User",
            phone_number="1234567890",
        )
        cls.seller = CustomUser.objects.create_user(
            username="seller",
            password="password",
            email="seller@example.com",
            first_name="Seller",
            last_name="User",
            phone_number="0987654321",
        )
        cls.admin = CustomUser.objects.create_superuser(
            username="admin",
            password="password",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            phone_number="1122334455",
        )
        cls.product = Product.objects.create(
            name="Test Product",
            price=100.0,
            images=[],
            description="Test Description",
            stock_quantity=10,
            seller=cls.seller,
        )
        cls.order = Order.objects.create(
            buyer=cls.buyer, seller=cls.seller, delivery_address="123 Test St"
        )
        cls.order.products.add(cls.product)

    def setUp(self):
        self.client.force_authenticate(user=self.buyer)

    def test_create_order(self):
        """Test creating an order."""
        url = reverse_lazy("orders")
        data = {
            "buyer": str(self.buyer.id),
            "seller": str(self.seller.id),
            "products": [str(self.product.id)],
            "delivery_address": "123 Test St",
        }
        response = self.client.post(url, data, format="json")
        order_data = response.data["data"]
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(order_data["buyer"], self.buyer.id)
        self.assertEqual(order_data["seller"], self.seller.id)
        self.assertEqual(order_data["delivery_address"], "123 Test St")

    def test_get_order(self):
        """Test retrieving an order."""
        url = reverse_lazy("order-by-id", args=[self.order.id])
        response = self.client.get(url)
        order_data = response.data["data"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(order_data["id"], str(self.order.id))
        self.assertEqual(order_data["buyer"], self.buyer.id)
        self.assertEqual(order_data["seller"], self.seller.id)
        self.assertEqual(order_data["delivery_address"], "123 Test St")

    def test_update_order_status(self):
        """Test updating the order status."""
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("update-order", args=[self.order.id])
        data = {
            "delivery_status": Order.DeliveryStatus.SHIPPED,
            "payment_status": Order.PaymentStatus.PAID,
        }
        response = self.client.put(url, data, format="json")
        order_data = response.data["data"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(order_data["delivery_status"], Order.DeliveryStatus.SHIPPED)
        self.assertEqual(order_data["payment_status"], Order.PaymentStatus.PAID)

    def test_update_order_status_non_admin(self):
        """Test that non-admin users cannot update the order status."""
        url = reverse_lazy("update-order", args=[self.order.id])
        data = {
            "delivery_status": Order.DeliveryStatus.SHIPPED,
            "payment_status": Order.PaymentStatus.PAID,
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)