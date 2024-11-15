from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import Product
from apps.users.models import CustomUser

from .models import Cart, CartItem


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class CartAPITest(TestCase):
    """Test cases for the Cart API views."""

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.user = CustomUser.objects.create_user(
            username="user",
            password="password",
            email="user@example.com",
            first_name="User",
            last_name="Test",
            phone_number="1234567890",
        )
        cls.product = Product.objects.create(
            name="Test Product",
            price=100.0,
            images=[],
            description="Test Description",
            stock_quantity=10,
            seller=cls.user,
        )
        cls.cart = Cart.objects.create(user=cls.user)
        cls.cart_item = CartItem.objects.create(
            user=cls.user, product=cls.product, quantity=2
        )
        cls.cart.items.add(cls.cart_item)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_cart(self):
        """Test retrieving the cart."""
        url = reverse_lazy("cart-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.user.id)
        self.assertEqual(response.data["total_price"], 200.0)

    def test_add_cart_item(self):
        """Test adding an item to the cart."""
        url = reverse_lazy("cartitem-list")
        data = {
            "user": self.user.id,
            "product": self.product.id,
            "quantity": 1,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"], self.user.id)
        self.assertEqual(response.data["product"], self.product.id)
        self.assertEqual(response.data["quantity"], 1)

    def test_update_cart_item(self):
        """Test updating an item in the cart."""
        url = reverse_lazy("cartitem-detail", args=[self.cart_item.id])
        data = {
            "quantity": 3,
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["quantity"], 3)

    def test_delete_cart_item(self):
        """Test deleting an item from the cart."""
        url = reverse_lazy("cartitem-detail", args=[self.cart_item.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_get_cart_unauthenticated(self):
        """Test that unauthenticated users cannot retrieve the cart."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("cart-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_cart_item_unauthenticated(self):
        """Test that unauthenticated users cannot add an item to the cart."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("cartitem-list")
        data = {
            "user": self.user.id,
            "product": self.product.id,
            "quantity": 1,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_cart_item_unauthenticated(self):
        """Test that unauthenticated users cannot update an item in the cart."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("cartitem-detail", args=[self.cart_item.id])
        data = {
            "quantity": 3,
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_cart_item_unauthenticated(self):
        """Test that unauthenticated users cannot delete an item from the cart."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("cartitem-detail", args=[self.cart_item.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
