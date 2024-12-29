from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import Product
from apps.users.models import CustomUser

from .models import Order, OrderItem


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
            role="seller",
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
            buyer=cls.buyer, delivery_address="123 Test St"
        )
        cls.order_item = OrderItem.objects.create(
            order=cls.order, product=cls.product, quantity=2
        )

    def test_order_creation(self):
        """Test that an order is created successfully."""
        self.assertEqual(self.order.buyer, self.buyer)
        self.assertEqual(self.order.delivery_address, "123 Test St")
        self.assertEqual(self.order.total_price, 200.0)
        self.assertEqual(self.order.delivery_fee, 10.0)
        self.assertIn(self.order_item, self.order.items.all())

    def test_order_str(self):
        """Test the string representation of the order."""
        self.assertEqual(str(self.order), f"Order - {self.order.id} by {self.buyer}")

    def test_order_item_str(self):
        """Test the string representation of the order item."""
        self.assertEqual(str(self.order_item), "2 x Test Product")


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
            role="seller",
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
            buyer=cls.buyer, delivery_address="123 Test St"
        )
        cls.order_item = OrderItem.objects.create(
            order=cls.order, product=cls.product, quantity=2
        )

        cls.other_seller = CustomUser.objects.create_user(
            username="other_seller",
            password="password",
            email="other@example.com",
            first_name="Other",
            last_name="Seller",
            phone_number="1234567890",
            role="seller",
        )
        cls.other_product = Product.objects.create(
            name="Other Product",
            price=100.0,
            images=[],
            description="Other Description",
            stock_quantity=10,
            seller=cls.other_seller,
        )
        cls.other_order = Order.objects.create(
            buyer=cls.buyer, delivery_address="123 Test St"
        )
        cls.other_order_item = OrderItem.objects.create(
            order=cls.other_order, product=cls.other_product, quantity=2
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer)

    def test_create_order(self):
        """Test creating an order."""
        url = reverse_lazy("orders")
        data = {
            "items": [
                {"product": str(self.product.id), "quantity": 2, "coupon": "DISCOUNT10"}
            ],
            "delivery_address": "123 Test St",
        }
        response = self.client.post(url, data, format="json")
        order_data = response.data.get("data")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(order_data["buyer"], self.buyer.id)
        self.assertEqual(order_data["delivery_address"], "123 Test St")

    def test_get_order(self):
        """Test retrieving an order."""
        url = reverse_lazy("order-by-id", args=[self.order.id])
        response = self.client.get(url)
        order_data = response.data["data"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(order_data["id"], str(self.order.id))
        self.assertEqual(order_data["buyer"], self.buyer.id)
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

    def test_create_order_unauthenticated(self):
        """Test that unauthenticated users cannot create an order."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("orders")
        data = {
            "items": [
                {"product": str(self.product.id), "quantity": 2, "coupon": "DISCOUNT10"}
            ],
            "delivery_address": "123 Test St",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_order_unauthenticated(self):
        """Test that unauthenticated users cannot retrieve an order."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("order-by-id", args=[self.order.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_order_status_unauthenticated(self):
        """Test that unauthenticated users cannot update the order status."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("update-order", args=[self.order.id])
        data = {
            "delivery_status": Order.DeliveryStatus.SHIPPED,
            "payment_status": Order.PaymentStatus.PAID,
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_seller_can_view_their_orders(self):
        """Test that a seller can view orders for their products."""
        self.client.force_authenticate(user=self.seller)
        url = reverse_lazy("seller-orders")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(self.order.id))
        self.assertEqual(len(response.data[0]["items"]), 1)
        self.assertEqual(
            str(response.data[0]["items"][0]["product"]), str(self.product.id)
        )

    def test_seller_cannot_view_other_seller_orders(self):
        """Test that a seller cannot view orders for other seller's products."""
        self.client.force_authenticate(user=self.seller)
        url = reverse_lazy("seller-orders")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(self.order.id))
        self.assertEqual(len(response.data[0]["items"]), 1)
        self.assertEqual(
            str(response.data[0]["items"][0]["product"]), str(self.product.id)
        )

    def test_non_seller_cannot_view_seller_orders(self):
        """Test that non-sellers cannot view orders for seller's products."""
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("seller-orders")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_view_seller_orders(self):
        """Test that unauthenticated users cannot view orders for seller's products."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("seller-orders")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_product_stock_decreases_on_order(self):
        """Test that the product stock decreases when an order is created."""
        initial_stock = self.product.stock_quantity
        url = reverse_lazy("orders")
        data = {
            "items": [
                {"product": str(self.product.id), "quantity": 2, "coupon": "DISCOUNT10"}
            ],
            "delivery_address": "123 Test St",
        }
        response = self.client.post(url, data, format="json")
        self.product.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.product.stock_quantity, initial_stock - 2)

    def test_cannot_order_more_than_available_stock(self):
        """Test that a user cannot order more than the available stock."""
        url = reverse_lazy("orders")
        data = {
            "items": [
                {
                    "product": str(self.product.id),
                    "quantity": 20,
                    "coupon": "DISCOUNT10",
                }
            ],
            "delivery_address": "123 Test St",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient stock for product", str(response.data))
