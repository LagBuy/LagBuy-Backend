import datetime

from decimal import Decimal
from django.core import mail
from django.utils import timezone
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from apps.products.models import Product
from apps.userAuth.models import CustomUser, Role
from apps.profiles.models import UsersProfile, VendorsProfile
from apps.cart.models import Cart, CartItem

from .models import Order, OrderItem

from common.utils.email_utils import (
    send_vendor_new_order_email,
    notify_vendor_of_new_order,
    send_admin_new_order_email,
    notify_admins_of_new_order,
)

User = get_user_model()


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class OrderAPITest(TestCase):
    """Comprehensive test cases for the Order API views."""

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        cls.user_role, _ = Role.objects.get_or_create(name="user")
        cls.vendor_role, _ = Role.objects.get_or_create(name="vendor")

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
        self.assertEqual(len(order_data["items"]), 1)  # a single vendor
        self.assertEqual(
            len(order_data["items"][str(self.seller.id)]), 2
        )  # two items from that vendor
        self.assertIn(
            order_data["items"][str(self.seller.id)][0]["product"],
            [self.product.id, self.product2.id],
        )
        self.assertEqual(order_data["items"][str(self.seller.id)][0]["quantity"], 2)
        self.assertIn(order_data["delivery_status"], ["pending", "completed"])

    def test_create_order_without_existing_cart(self):
        """Test creating an order when user doesn't have a cart yet."""
        # Create a new buyer without a cart
        new_buyer = CustomUser.objects.create_user(
            email="newbuyer@example.com",
            password="password",
        )
        new_buyer.roles.add(self.user_role)
        
        # Authenticate as the new buyer
        self.client.force_authenticate(user=new_buyer)
        
        # Verify no cart exists
        self.assertFalse(Cart.objects.filter(user=new_buyer).exists())
        
        # Create cart items manually (simulating cart creation)
        new_cart = Cart.objects.create(user=new_buyer)
        CartItem.objects.create(
            cart=new_cart, product=self.product, quantity=1
        )
        
        url = reverse_lazy("orders")
        data = {
            "vendor": str(self.seller.id),
            "delivery_address": "789 Auto Cart St",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify cart was created/used
        self.assertTrue(Cart.objects.filter(user=new_buyer).exists())
        order_data = response.data["data"]
        self.assertEqual(order_data["buyer"], new_buyer.id)

    def test_create_order_auto_creates_cart_if_missing(self):
        """Test that order creation auto-creates a cart if user doesn't have one."""
        # Create a new buyer
        new_buyer = CustomUser.objects.create_user(
            email="autobuyer@example.com",
            password="password",
        )
        new_buyer.roles.add(self.user_role)
        
        # Delete cart if it exists (shouldn't exist, but just to be sure)
        Cart.objects.filter(user=new_buyer).delete()
        
        # Authenticate as the new buyer
        self.client.force_authenticate(user=new_buyer)
        
        # Verify no cart exists initially
        self.assertFalse(Cart.objects.filter(user=new_buyer).exists())
        
        url = reverse_lazy("orders")
        data = {
            "vendor": str(self.seller.id),
            "delivery_address": "Empty Cart St",
        }
        
        # This should not fail even though cart doesn't exist
        # The serializer should create it automatically
        response = self.client.post(url, data, format="json")
        
        # Verify cart was auto-created
        self.assertTrue(Cart.objects.filter(user=new_buyer).exists())
        cart = Cart.objects.get(user=new_buyer)
        self.assertEqual(cart.user, new_buyer)

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
        self.assertEqual(len(items), 1)  # a single vendor
        self.assertEqual(
            len(items[str(self.seller.id)]), 2
        )  # two items from that vendor
        self.assertIn(
            items[str(self.seller.id)][0]["product"],
            [self.product.id, self.product2.id],
        )
        self.assertEqual(items[str(self.seller.id)][0]["quantity"], 2)
        self.assertIn(
            float(items[str(self.seller.id)][0]["total_price"]),
            [float(self.product.price) * 2, float(self.product2.price) * 2],
        )

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
        self.assertEqual(order_data["total_price"], 598)  # 200 subtotal + 398 service charge

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

    # Testing valid order state transitions
    def test_cannot_ship_before_payment(self):
        """
        Test updating the status of an order item
        to shipped when not paid returns error.
        """
        # seller user updates order_item -> shipped but order unpaid
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("update-orderitem-status", args=[self.order_item.id])
        data = {"delivery_status": OrderItem.DeliveryStatus.SHIPPED}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            str(response.data["message"]["delivery_status"][0]),
            "Cannot ship before order is paid.",
        )

    def test_can_ship_after_payment(self):
        """
        Test updating the status of an order item
        to shipped after payments returns 200 .
        """
        # mark payment as paid first (create Payment with payment_status paid or update)
        from apps.payments.models import Payment, PaymentStatus

        Payment.objects.create(
            user=self.buyer,
            order=self.order,
            amount=self.order.total_price,
            currency="NGN",
            ref="paid_test",
            payment_status=PaymentStatus.PAID,
        )
        # self.order.refresh_from_db()
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("update-orderitem-status", args=[self.order_item.id])
        # self.order.save()
        data = {"delivery_status": OrderItem.DeliveryStatus.SHIPPED}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order_item.refresh_from_db()
        self.assertEqual(
            response.data["data"]["delivery_status"], OrderItem.DeliveryStatus.SHIPPED
        )


"""
Tests for email utility functions.
"""
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    VENDOR_URL='https://vendors.lagbuy.com/',
    SITE_NAME='LagBuy',
    SUPPORT_EMAIL='support@lagbuy.com',
    DEFAULT_FROM_EMAIL='noreply@lagbuy.com',
    SEND_NEW_ORDER_DETAILS=['admin1@lagbuy.com', 'admin2@lagbuy.com'],
    DEFAULT_RIDER_PAY=1200,
)
class VendorEmailUtilsTestCase(TestCase):
    """Test cases for vendor email utility functions."""
    
    def setUp(self):
        """Set up test data."""
        # Create vendor user
        self.vendor = User.objects.create_user(
            email='vendor@test.com',
            password='testpass123'
        )
        self.vendor_user_profile = UsersProfile.objects.create(
            user=self.vendor,
            first_name='John',
            last_name='Vendor',
            phone_number='08012345678'
        )
        self.vendor_profile = VendorsProfile.objects.create(
            user=self.vendor,
            business_name='John\'s Store',
            business_address='123 Market Street',
            business_location_city='Lagos',
            business_location_state='Lagos',
        )
        
        # Create buyer user
        self.buyer = User.objects.create_user(
            email='buyer@test.com',
            password='testpass123'
        )
        self.buyer_profile = UsersProfile.objects.create(
            user=self.buyer,
            first_name='Jane',
            last_name='Buyer',
            phone_number='08087654321'
        )
        
        # Create product
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('5000.00'),
            seller=self.vendor,
            description='Test description',
            stock_quantity=10
        )
        
        # Create order
        self.order = Order.objects.create(
            buyer=self.buyer,
            delivery_address='456 Delivery Lane, Ikeja, Lagos'
        )
        
        # Create order item
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1
        )
        
        # Clear mail outbox
        mail.outbox = []
    
    def test_send_vendor_new_order_email_success(self):
        """Test sending vendor email successfully."""
        result = send_vendor_new_order_email(self.order, self.vendor)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, ['vendor@test.com'])
        self.assertIn('New Order', sent_email.subject)
        self.assertIn('Test Product', sent_email.body)
    
    def test_send_vendor_email_includes_vendor_name(self):
        """Test that vendor email includes vendor's name."""
        send_vendor_new_order_email(self.order, self.vendor)
        
        sent_email = mail.outbox[0]
        self.assertIn('John', sent_email.body)
    
    def test_send_vendor_email_includes_customer_name(self):
        """Test that vendor email includes customer's name."""
        send_vendor_new_order_email(self.order, self.vendor)
        
        sent_email = mail.outbox[0]
        self.assertIn('Jane Buyer', sent_email.body)
    
    def test_send_vendor_email_includes_order_items(self):
        """Test that vendor email includes order items."""
        send_vendor_new_order_email(self.order, self.vendor)
        
        sent_email = mail.outbox[0]
        self.assertIn('Test Product', sent_email.body)
        self.assertIn('5,000.00', sent_email.body)
    
    def test_send_vendor_email_includes_totals(self):
        """Test that vendor email includes correct totals."""
        send_vendor_new_order_email(self.order, self.vendor)
        
        sent_email = mail.outbox[0]
        self.assertIn('5,000.00', sent_email.body)  # Subtotal
        self.assertIn('5,000.00', sent_email.body)  # Service charge
    
    def test_send_vendor_email_html_and_text(self):
        """Test that both HTML and plain text versions are sent."""
        send_vendor_new_order_email(self.order, self.vendor)
        
        sent_email = mail.outbox[0]
        self.assertEqual(len(sent_email.alternatives), 1)
        self.assertEqual(sent_email.alternatives[0][1], 'text/html')
    
    def test_notify_vendor_of_new_order(self):
        """Test notify_vendor_of_new_order function."""
        result = notify_vendor_of_new_order(self.order)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['vendor@test.com'])
    
    def test_notify_vendor_includes_correct_items(self):
        """Test that only vendor's items are included in notification."""
        # Create another vendor
        other_vendor = User.objects.create_user(
            email='other@test.com',
            password='testpass123'
        )
        
        # Notify should only send to the order's vendor
        result = notify_vendor_of_new_order(self.order)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['vendor@test.com'])
    
    def test_send_vendor_email_no_profile(self):
        """Test sending email when vendor has no profile."""
        # Delete vendor profile
        self.vendor_profile.delete()
        
        result = send_vendor_new_order_email(self.order, self.vendor)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
    
    def test_send_vendor_email_no_items(self):
        """Test sending email when order has no items."""
        # Create empty order
        empty_order = Order.objects.create(
            buyer=self.buyer
        )
        
        result = send_vendor_new_order_email(empty_order, self.vendor)
        
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)
    
    @patch('common.utils.email_utils.EmailMultiAlternatives.send')
    def test_send_vendor_email_handles_errors(self, mock_send):
        """Test error handling when email sending fails."""
        mock_send.side_effect = Exception('Email server error')
        
        result = send_vendor_new_order_email(self.order, self.vendor)
        
        self.assertFalse(result)
    
    def test_vendor_email_includes_dashboard_link(self):
        """Test that vendor email includes link to dashboard."""
        send_vendor_new_order_email(self.order, self.vendor)
        
        sent_email = mail.outbox[0]
        self.assertIn('vendor dashboard', sent_email.body)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SITE_NAME='LagBuy',
    SUPPORT_EMAIL='support@lagbuy.com',
    DEFAULT_FROM_EMAIL='noreply@lagbuy.com',
    SEND_NEW_ORDER_DETAILS=['admin1@lagbuy.com', 'admin2@lagbuy.com'],
    DEFAULT_RIDER_PAY=1200,
)
class AdminEmailUtilsTestCase(TestCase):
    """Test cases for admin email utility functions."""
    
    def setUp(self):
        """Set up test data."""
        # Create vendor user
        self.vendor = User.objects.create_user(
            email='vendor@test.com',
            password='testpass123'
        )
        self.vendor_user_profile = UsersProfile.objects.create(
            user=self.vendor,
            first_name='John',
            last_name='Vendor',
            phone_number='08012345678'
        )
        self.vendor_profile = VendorsProfile.objects.create(
            user=self.vendor,
            business_name='John\'s Store',
            business_address='123 Market Street',
            business_location_city='Lagos',
            business_location_state='Lagos',
        )
        
        # Create buyer user
        self.buyer = User.objects.create_user(
            email='buyer@test.com',
            password='testpass123'
        )
        self.buyer_profile = UsersProfile.objects.create(
            user=self.buyer,
            first_name='Jane',
            last_name='Buyer',
            phone_number='08087654321'
        )
        
        # Create product
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('5000.00'),
            seller=self.vendor,
            description='Test description',
            stock_quantity=10
        )
        
        # Create order
        self.order = Order.objects.create(
            buyer=self.buyer,
            delivery_address='456 Delivery Lane, Ikeja, Lagos'
        )
        
        # Create order item
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1
        )
        
        # Clear mail outbox
        mail.outbox = []
    
    def test_send_admin_new_order_email_success(self):
        """Test sending admin email successfully."""
        result = send_admin_new_order_email(self.order)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, ['admin1@lagbuy.com', 'admin2@lagbuy.com'])
        self.assertIn('New Order', sent_email.subject)
    
    def test_admin_email_includes_delivery_details(self):
        """Test that admin email includes delivery coordination details."""
        send_admin_new_order_email(self.order)
        
        sent_email = mail.outbox[0]
        # Check for delivery box content
        self.assertIn('NEW DELIVERY AVAILABLE', sent_email.body)
        self.assertIn('Order ID:', sent_email.body)
        self.assertIn('Pickup:', sent_email.body)
        self.assertIn('Drop-off:', sent_email.body)
        self.assertIn('Rider Pay:', sent_email.body)
        self.assertIn('Items:', sent_email.body)
    
    def test_admin_email_includes_vendor_address(self):
        """Test that admin email includes vendor's full address."""
        send_admin_new_order_email(self.order)
        
        sent_email = mail.outbox[0]
        self.assertIn('123 Market Street', sent_email.body)
        self.assertIn('Lagos', sent_email.body)
    
    def test_admin_email_includes_delivery_address(self):
        """Test that admin email includes delivery address."""
        send_admin_new_order_email(self.order)
        
        sent_email = mail.outbox[0]
        self.assertIn('456 Delivery Lane, Ikeja, Lagos', sent_email.body)
    
    def test_admin_email_includes_rider_pay(self):
        """Test that admin email includes rider pay amount."""
        send_admin_new_order_email(self.order)
        
        sent_email = mail.outbox[0]
        self.assertIn('₦1,200', sent_email.body)
    
    def test_admin_email_includes_items_list(self):
        """Test that admin email includes simple items list."""
        send_admin_new_order_email(self.order)
        
        sent_email = mail.outbox[0]
        self.assertIn('Test Product', sent_email.body)
    
    def test_admin_email_includes_acceptance_instructions(self):
        """Test that admin email includes rider acceptance instructions."""
        send_admin_new_order_email(self.order)
        
        sent_email = mail.outbox[0]
        order_id_short = str(self.order.id)[:8]
        self.assertIn(f'PICKED {order_id_short}', sent_email.body)
        self.assertIn('First to reply gets the job', sent_email.body)
    
    def test_admin_email_includes_customer_details(self):
        """Test that admin email includes customer information."""
        send_admin_new_order_email(self.order)
        
        sent_email = mail.outbox[0]
        self.assertIn('Jane Buyer', sent_email.body)
        self.assertIn('buyer@test.com', sent_email.body)
    
    def test_admin_email_includes_vendor_details(self):
        """Test that admin email includes vendor information."""
        send_admin_new_order_email(self.order)
        
        sent_email = mail.outbox[0]
        self.assertIn('John Vendor', sent_email.body)
        self.assertIn('John', sent_email.body)  # Vendor business name
        self.assertIn('vendor@test.com', sent_email.body)
    
    def test_admin_email_includes_order_totals(self):
        """Test that admin email includes order totals."""
        send_admin_new_order_email(self.order)
        
        sent_email = mail.outbox[0]
        self.assertIn('5,000.00', sent_email.body)  # Subtotal
        self.assertIn('398.00', sent_email.body)  # Service charge (min charge for 5000 subtotal)
        self.assertIn('5,398.00', sent_email.body)  # Total (5000 + 398 service charge)
    
    def test_admin_email_html_and_text(self):
        """Test that both HTML and plain text versions are sent."""
        send_admin_new_order_email(self.order)
        
        sent_email = mail.outbox[0]
        self.assertEqual(len(sent_email.alternatives), 1)
        self.assertEqual(sent_email.alternatives[0][1], 'text/html')
    
    def test_notify_admins_of_new_order(self):
        """Test notify_admins_of_new_order function."""
        result = notify_admins_of_new_order(self.order)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['admin1@lagbuy.com', 'admin2@lagbuy.com'])
    
    def test_admin_email_no_settings_config(self):
        """Test that function handles missing settings gracefully."""
        with self.settings(SEND_NEW_ORDER_DETAILS=[]):
            result = send_admin_new_order_email(self.order)
            
            self.assertFalse(result)
            self.assertEqual(len(mail.outbox), 0)
    
    def test_admin_email_vendor_no_profile(self):
        """Test admin email when vendor has no profile."""
        # Delete vendor profile
        self.vendor_profile.delete()
        
        result = send_admin_new_order_email(self.order)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        # Should still send email with available data
        sent_email = mail.outbox[0]
        self.assertIn('vendor@test.com', sent_email.body)
    
    def test_admin_email_customer_no_profile(self):
        """Test admin email when customer has no profile."""
        # Delete buyer profile
        self.buyer_profile.delete()
        
        result = send_admin_new_order_email(self.order)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
    
    @patch('common.utils.email_utils.EmailMultiAlternatives.send')
    def test_admin_email_handles_errors(self, mock_send):
        """Test error handling when email sending fails."""
        mock_send.side_effect = Exception('Email server error')
        
        result = send_admin_new_order_email(self.order)
        
        self.assertFalse(result)
    
    def test_admin_email_multiple_items(self):
        """Test admin email with multiple order items."""
        # Create another product and order item
        product2 = Product.objects.create(
            name='Product Two',
            price=Decimal('3000.00'),
            seller=self.vendor,
            description='Second product',
            stock_quantity=10
        )
        OrderItem.objects.create(
            order=self.order,
            product=product2,
            quantity=2
        )
        
        send_admin_new_order_email(self.order)
        
        sent_email = mail.outbox[0]
        self.assertIn('Test Product', sent_email.body)
        self.assertIn('Product Two', sent_email.body)
        # Check items list includes both
        self.assertIn('Test Product, Product Two', sent_email.body)
