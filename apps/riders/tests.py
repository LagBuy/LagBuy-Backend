from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import Product
from apps.userAuth.models import CustomUser, Role
from apps.profiles.models import VendorsProfile

from apps.orders.models import Order, OrderItem


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class RiderAPITest(TestCase):
    """Comprehensive test cases for the Order API views."""

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        cls.user_role, _ = Role.objects.get_or_create(name="user")
        cls.vendor_role, _ = Role.objects.get_or_create(name="vendor")
        cls.rider_role, _ = Role.objects.get_or_create(name="rider")

        cls.buyer = CustomUser.objects.create_user(
            email="buyer@example.com",
            password="password",
        )
        cls.buyer.roles.add(cls.user_role)

        cls.seller = CustomUser.objects.create_user(
            email="seller@example.com",
            password="password",
        )
        VendorsProfile.objects.create(
            user=cls.seller,
            business_address="Test vendors address"
        )
        cls.seller.roles.add(cls.user_role)
        cls.seller.roles.add(cls.vendor_role)

        cls.rider = CustomUser.objects.create_user(
            email="rider@example.com",
            password="password",
        )
        cls.rider.roles.add(cls.user_role)
        cls.rider.roles.add(cls.rider_role)

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
        cls.order = Order.objects.create(
            buyer=cls.buyer, delivery_address="123 Test St"
        )
        cls.order_item = OrderItem.objects.create(
            order=cls.order, product=cls.product, quantity=2,
        )
        cls.order_item.assigned_riders.add(cls.rider)

        cls.order2 = Order.objects.create(
            buyer=cls.buyer, delivery_address="123 Test St",
        )
        cls.order_item2 = OrderItem.objects.create(
            order=cls.order, product=cls.product, quantity=1, rider=cls.buyer, ready_for_pickup=True
        )
        cls.order_item2.assigned_riders.add(cls.rider)

        cls.order3 = Order.objects.create(
            buyer=cls.buyer, delivery_address="123 Test St"
        )
        cls.order_item3 = OrderItem.objects.create(
            order=cls.order3, product=cls.product, quantity=3,
            delivery_status=OrderItem.DeliveryStatus.DELIVERED, rider=cls.rider,
            ready_for_pickup=True
        )
        cls.order_item3.assigned_riders.add(cls.rider)

        cls.order_item4 = OrderItem.objects.create(
            order=cls.order3, product=cls.product, quantity=3,
            delivery_status=OrderItem.DeliveryStatus.DELIVERED,
            ready_for_pickup=True
        )
        cls.order_item4.assigned_riders.add(cls.buyer)

        cls.order_item5 = OrderItem.objects.create(
            order=cls.order3, product=cls.product, quantity=3,
            delivery_status=OrderItem.DeliveryStatus.PENDING, rider=cls.rider,
            ready_for_pickup=True
        )
        cls.order_item5.assigned_riders.add(cls.rider)

        cls.order_item6 = OrderItem.objects.create(
            order=cls.order3, product=cls.product, quantity=3,
            delivery_status=OrderItem.DeliveryStatus.PENDING,
            ready_for_pickup=True
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.rider)
    
    def test_view_all_assigned_items(self):
        """Test viewing all orders that has been assigned to a rider"""
        url = reverse_lazy("get-all-assigned-order")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"][0]
        self.assertEqual(len(response.data["data"]), 1, "only one order available to be accepted")
        self.assertEqual(data["id"], str(self.order_item.id))
        self.assertEqual(data["product"], self.product.id)
        self.assertEqual(data["delivery_status"], "PENDING")
        self.assertIsNone(data["rider"])
        self.assertIsNotNone(data["delivery_address"])
        self.assertIsNotNone(data["pickup_address"])
        self.assertEqual("Test vendors address", data["pickup_address"])
    
    def test_accept_or_decline_item(self):
        """Test the accept or decline assigned item view"""
        url = reverse_lazy("accept-or-decline-assigned-order", args=[self.order_item.id])
        response = self.client.put(url, { "accept": True }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Item accepted successfully")
        self.order_item.refresh_from_db()
        self.assertIsNotNone(self.order_item.rider)
        self.assertEqual(self.order_item.rider, self.rider)
    
    def test_accept_or_decline_item_wrong_input(self):
        """Test the accept or decline assigned item view with wrong input"""
        url = reverse_lazy("accept-or-decline-assigned-order", args=[self.order_item.id])
        response = self.client.put(url, { "accept": "yes" }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Wrong query parameter: `accept`, should be set to true or false")
    
    def test_accept_or_decline_item_no_data(self):
        """Test the accept or decline assigned item view with no data"""
        url = reverse_lazy("accept-or-decline-assigned-order", args=[self.order_item.id])
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Missing required query parameter: `accept`, should be set to true or false")

    def test_accept_or_decline_item_wrong_item(self):
        """Test the accept or decline assigned item view with the wrong item"""
        url = reverse_lazy("accept-or-decline-assigned-order", args=[self.order_item4.id])
        response = self.client.put(url, { "accept": True }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Item is not assinged to rider")

    def test_accept_or_decline_order_already_assigned(self):
        """Test the accept or decline assigned item view when the order has already been assigned"""
        url = reverse_lazy("accept-or-decline-assigned-order", args=[self.order_item3.id])
        response = self.client.put(url, { "accept": True }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Item not found or has been accepted by another rider")
    
    def test_get_rider_undelivered_items(self):
        """Test get undelivered but accepted item view"""
        url = reverse_lazy("get-all-undelivered-items")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        data = response.data["data"][0]
        self.assertEqual(data["id"], str(self.order_item5.id))
        self.assertEqual(data["product"], self.product.id)
        self.assertEqual(data["delivery_status"], "PENDING")
        self.assertIsNotNone(data["rider"])
        self.assertIsNotNone(data["delivery_address"])

    def test_get_rider_delivered_items(self):
        """Test get rider delivered item view"""
        url = reverse_lazy("get-all-delivered-items")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        data = response.data["data"][0]
        self.assertEqual(data["id"], str(self.order_item3.id))
        self.assertEqual(data["product"], self.product.id)
        self.assertEqual(data["delivery_status"], "DELIVERED")
        self.assertIsNotNone(data["rider"])
        self.assertIsNotNone(data["delivery_address"])

    def test_admin_list_all_items(self):
        """Test admin list all items ready for pickup"""
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("admin-list-all-items")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 3)
        data = response.data["data"][0]
        self.assertEqual(data["delivery_status"], "PENDING")
        self.assertEqual(response.data["data"][1]["delivery_status"], "PENDING")
        self.assertEqual(data["ready_for_pickup"], True)

    def test_admin_assign_items(self):
        """Test admin assign items to riders view"""
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("admin-item-assign", args=[self.order_item6.id])
        response = self.client.put(url, data={ "assigned_riders": [self.rider.id] })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertIn(self.rider.id, data["assigned_riders"])

    def test_admin_assign_items_with_wrong_user_type(self):
        """Test admin assign items to riders view with wrong user type"""
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("admin-item-assign", args=[self.order_item6.id])
        response = self.client.put(url, data={ "assigned_riders": [self.buyer.id] })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_admin_assign_items_with_no_data(self):
        """Test admin assign items to riders view with no data"""
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("admin-item-assign", args=[self.order_item6.id])
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "No data provided")

    def test_admin_assign_items_with_wrong_item_id(self):
        """Test admin assign items to riders view with wrong item ID"""
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("admin-item-assign", args=[self.order.id])
        response = self.client.put(url, data={ "assigned_riders": [self.buyer.id] })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Invalid Item ID")

    def test_admin_assign_items_with_delivered_item(self):
        """Test admin assign items to riders view with delivered item"""
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("admin-item-assign", args=[self.order_item4.id])
        response = self.client.put(url, data={ "assigned_riders": [self.buyer.id] })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_assign_items_with_item_not_ready_for_pickup(self):
        """Test admin assign items to riders view with item not ready for pickup"""
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("admin-item-assign", args=[self.order_item.id])
        response = self.client.put(url, data={ "assigned_riders": [self.buyer.id] })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

