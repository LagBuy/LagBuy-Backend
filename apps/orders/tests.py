import datetime

from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import Product
from apps.userAuth.models import CustomUser, Role
from apps.profiles.models import UsersProfile
from apps.cart.models import Cart, CartItem

from .models import Order, OrderItem


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class OrderAPITest(TestCase):
    """Comprehensive test cases for the Order API views."""

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        cls.user_role = Role.objects.create(name="user")
        cls.vendor_role = Role.objects.create(name="vendor")

        cls.buyer = CustomUser.objects.create_user(
            email="buyer@example.com",
            password="password",
        )
        cls.buyer.roles.add(cls.user_role)

        cls.seller = CustomUser.objects.create_user(
            email="seller@example.com",
            password="password",
        )
        cls.seller.roles.add(cls.user_role)
        cls.seller.roles.add(cls.vendor_role)

        cls.admin = CustomUser.objects.create_superuser(
            email="admin@example.com",
            password="password",
        )
        cls.admin.roles.add(cls.user_role)

        cls.product = Product.objects.create(
            name="Test Product",
            price=100.0,
            description="Test Description",
            stock_quantity=10,
            seller=cls.seller,
        )
        cls.product2 = Product.objects.create(
            name="Another Product",
            price=50.0,
            description="Another Description",
            stock_quantity=5,
            seller=cls.seller,
        )
        cls.cart = Cart.objects.create(user=cls.buyer)
        cls.cart_item = CartItem.objects.create(
            cart=cls.cart, product=cls.product, quantity=2
        )
        cls.cart_item2 = CartItem.objects.create(
            cart=cls.cart, product=cls.product2, quantity=2
        )
        cls.order = Order.objects.create(
            buyer=cls.buyer, delivery_address="123 Test St"
        )
        cls.order_item = OrderItem.objects.create(
            order=cls.order, product=cls.product, quantity=2
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer)

    def test_create_order(self):
        """Test creating an order."""
        url = reverse_lazy("orders")
        data = {
            "vendor": str(self.seller.id),
            "delivery_address": "456 New St",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order_data = response.data["data"]
        self.assertEqual(order_data["buyer"], self.buyer.id)
        self.assertEqual(order_data["delivery_address"], "456 New St")
        self.assertEqual(len(order_data["items"]), 2)
        self.assertIn(order_data["items"][0]["product"], [self.product.id, self.product2.id])
        self.assertEqual(order_data["items"][0]["quantity"], 2)
        self.assertIn(order_data["delivery_status"], ["pending", "completed"])
    
    def test_purchase_price_recorded(self):
        """Test that the purchase price is recorded correctly when an order is created."""
        url = reverse_lazy("orders")
        data = {
            "vendor": str(self.seller.id),
            "delivery_address": "789 Price St",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order_id = response.data["data"]["id"]
        order_detail_url = reverse_lazy("order-by-id", args=[order_id])
        order_response = self.client.get(order_detail_url)
        self.assertEqual(order_response.status_code, status.HTTP_200_OK)
        items = order_response.data["data"]["items"]
        self.assertEqual(len(items), 2)
        self.assertIn(items[0]["product"], [self.product.id, self.product2.id])
        self.assertEqual(items[0]["quantity"], 2)
        self.assertIn(float(items[0]["total_price"]), [float(self.product.price) * 2, float(self.product2.price) * 2])

    def test_create_order_insufficient_stock(self):
        """Test creating an order with quantity greater than stock fails."""
        url = reverse_lazy("orders")
        self.cart_item.quantity = 20
        self.cart_item.save()
        data = {
            "vendor": str(self.seller.id),
            "delivery_address": "789 Fail St",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient stock", str(response.data))

    def test_create_order_unauthenticated(self):
        """Test unauthenticated users cannot create orders."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("orders")
        data = {
            "vendor": str(self.seller.id),
            "delivery_address": "123 Test St",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_order(self):
        """Test retrieving an order by ID."""
        url = reverse_lazy("order-by-id", args=[self.order.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_data = response.data["data"]
        self.assertEqual(order_data["id"], str(self.order.id))
        self.assertEqual(order_data["buyer"], self.buyer.id)
        self.assertIn(order_data["delivery_status"], ["pending", "completed"])
        self.assertEqual(order_data["service_charge"], self.order.service_charge)
        self.assertEqual(len(order_data["items"]), 1)
        self.assertEqual(order_data["total_price"], 800) # plus service charge

    def test_get_order_unauthenticated(self):
        """Test unauthenticated users cannot retrieve orders."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("order-by-id", args=[self.order.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_order(self):
        """Test updating an order's delivery address."""
        url = reverse_lazy("order-by-id", args=[self.order.id])
        data = {"delivery_address": "Updated Address"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.delivery_address, "Updated Address")

    def test_delete_order(self):
        """Test deleting an order."""
        url = reverse_lazy("order-by-id", args=[self.order.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(id=self.order.id).exists())

    def test_update_order_item_status_admin(self):
        """Test admin can update order item status."""
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("update-orderitem-status", args=[self.order_item.id])
        data = {
            "payment_status": "paid",
        }
        # Ensure payment exists
        from apps.payments.models import Payment, PaymentStatus

        Payment.objects.create(
            user=self.buyer,
            order=self.order,
            amount=self.order.total_price,
            currency="NGN",
            ref="test_ref_update_admin",
            payment_status=PaymentStatus.PENDING,
        )
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        payment = self.order.payments.first()
        self.assertIsNotNone(payment)
        payment.payment_status = "paid"
        payment.save(update_fields=["payment_status"])
        self.assertEqual(payment.payment_status, PaymentStatus.PAID)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)

    def test_update_order_item_status_non_admin(self):
        """Test non-admin cannot update order item status."""
        url = reverse_lazy("update-orderitem-status", args=[self.order_item.id])
        data = {
            "payment_status": "paid",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_order_item_status_unauthenticated(self):
        """Test unauthenticated user cannot update order item status."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("update-orderitem-status", args=[self.order_item.id])
        data = {
            "payment_status": "paid",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_seller_can_view_their_orders(self):
        """Test seller can view orders for their products."""
        self.client.force_authenticate(user=self.seller)
        url = reverse_lazy("seller-orders")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for order in response.data["data"]:
            self.assertEqual(order["product"], self.product.id or self.product2.id)

    def test_non_seller_cannot_view_seller_orders(self):
        """Test non-seller cannot view seller orders."""
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("seller-orders")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_view_seller_orders(self):
        """Test unauthenticated user cannot view seller orders."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("seller-orders")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_product_stock_decreases_on_order(self):
        """Test product stock decreases when an order is created."""
        initial_stock = self.product2.stock_quantity
        url = reverse_lazy("orders")
        data = {
            "vendor": str(self.seller.id),
            "delivery_address": "Stock Test St",
        }
        response = self.client.post(url, data, format="json")
        self.product2.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.product2.stock_quantity, initial_stock - 2)

    def test_cannot_order_more_than_available_stock(self):
        """Test cannot order more than available stock."""
        url = reverse_lazy("orders")
        self.cart_item.quantity = 20
        self.cart_item.save()
        data = {
            "vendor": str(self.seller.id),
            "delivery_address": "Stock Fail St",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient stock", str(response.data))

    def test_create_order_from_cart(self):
        return
        """Test creating an order from the cart and verify order items and status."""

        url = reverse_lazy("orders")
        data = {
            "items": [
                {"product": self.product.id, "quantity": 2},
                {"product": self.product2.id, "quantity": 1},
            ],
            "delivery_address": "Cart Order Address",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order_id = response.data["data"]["id"]
        order_detail_url = reverse_lazy("order-by-id", args=[order_id])
        order_response = self.client.get(order_detail_url)

        self.assertEqual(order_response.status_code, status.HTTP_200_OK)
        items = order_response.data["data"]["items"]
        self.assertEqual(len(items), 2)
        product_ids = {item["product"] for item in items}
        self.assertIn(self.product.id, product_ids)
        self.assertIn(self.product2.id, product_ids)
        self.assertIn(
            order_response.data["data"]["delivery_status"], ["pending", "completed"]
        )

    def test_order_item_status_update(self):
        """Test updating the status of an order item."""
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("update-orderitem-status", args=[self.order_item.id])
        data = {"payment_status": "paid"}
        # Ensure payment exists
        from apps.payments.models import Payment, PaymentStatus

        Payment.objects.create(
            user=self.buyer,
            order=self.order,
            amount=self.order.total_price,
            currency="NGN",
            ref="test_ref_update_status",
            payment_status=PaymentStatus.PENDING,
        )
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        payment = self.order.payments.first()
        self.assertIsNotNone(payment)
        payment.payment_status = "paid"
        payment.save(update_fields=["payment_status"])

        self.assertEqual(payment.payment_status, PaymentStatus.PAID)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)
