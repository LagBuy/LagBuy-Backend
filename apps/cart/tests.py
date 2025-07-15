import datetime

from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import Product
from apps.userAuth.models import CustomUser, Role

from .models import Cart, CartItem


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class CartAPITest(TestCase):
    """Comprehensive test cases for the Cart and CartItem API views."""

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.user_role = Role.objects.create(name='user')
        cls.vendor_role = Role.objects.create(name='vendor')

        cls.user = CustomUser.objects.create_user(
            email="user@example.com",
            password="password",
        )
        cls.user.roles.add(cls.user_role)

        cls.other_user = CustomUser.objects.create_user(
            email="otheruser@example.com",
            password="password",
        )
        cls.other_user.roles.add(cls.user_role)

        cls.product = Product.objects.create(
            name="Test Product",
            price=100.0,
            description="Test Description",
            stock_quantity=10,
            seller=cls.user,
        )
        cls.product2 = Product.objects.create(
            name="Another Product",
            price=50.0,
            description="Another Description",
            stock_quantity=5,
            seller=cls.user,
        )
        cls.cart = Cart.objects.create(user=cls.user)
        cls.cart_item = CartItem.objects.create(
            cart=cls.cart, product=cls.product, quantity=2
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_cart(self):
        """Test retrieving the authenticated user's cart."""
        url = reverse_lazy("cart-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["user"], self.user.id)
        self.assertEqual(response.data["data"]["total_price"], 200.0)
        self.assertEqual(len(response.data["data"]["items"]), 1)

    def test_get_cart_creates_if_not_exists(self):
        """Test that a cart is created if it does not exist."""
        self.client.force_authenticate(user=self.other_user)
        url = reverse_lazy("cart-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["user"], self.other_user.id)
        self.assertEqual(response.data["data"]["total_price"], 0)
        self.assertEqual(len(response.data["data"]["items"]), 0)

    def test_clear_cart(self):
        """Test clearing the cart (deleting all items)."""
        url = reverse_lazy("cart-list")
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.items.count(), 0)

    def test_clear_cart_not_found(self):
        """Test clearing a cart that does not exist returns 404."""
        self.client.force_authenticate(user=self.other_user)
        url = reverse_lazy("cart-list")
        # Delete the cart if it exists
        Cart.objects.filter(user=self.other_user).delete()
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_cart_item(self):
        """Test adding a new item to the cart using add_item action."""
        url = reverse_lazy("add-cartitem")
        data = {
            "product": self.product2.id,
            "quantity": 3,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["product"]["id"], str(self.product2.id))
        self.assertEqual(response.data["data"]["quantity"], 3)
        self.assertEqual(
            CartItem.objects.filter(cart=self.cart, product=self.product2).count(), 1
        )

    def test_add_existing_cart_item_increments_quantity(self):
        """Test adding an existing product to the cart increments its quantity using add_item action."""
        url = reverse_lazy("add-cartitem")
        data = {"product": self.product.id}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["quantity"], 3)
        self.cart_item.refresh_from_db()
        self.assertEqual(self.cart_item.quantity, 3)

    def test_update_cart_item_quantity(self):
        """Test updating the quantity of a cart item using add_item action (should set quantity)."""
        url = reverse_lazy("add-cartitem")
        data = {"product": self.product.id, "quantity": 5}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cart_item.refresh_from_db()
        self.assertEqual(self.cart_item.quantity, 5)

    def test_remove_cart_item(self):
        """Test removing a cart item using remove_item action."""
        url = reverse_lazy("remove-cartitem")
        data = {"item_id": self.cart_item.id}
        response = self.client.delete(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(CartItem.objects.filter(id=self.cart_item.id).exists())

    def test_remove_cart_item_not_found(self):
        """Test removing a non-existent cart item returns 404."""
        url = reverse_lazy("remove-cartitem")
        data = {"item_id": 99999}
        response = self.client.delete(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_cart_items(self):
        """Test listing all items in the user's cart."""
        url = reverse_lazy("cartitem-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(
            response.data["data"][0]["product"]["id"], str(self.product.id)
        )

    def test_retrieve_cart_item(self):
        """Test retrieving a specific cart item."""
        url = reverse_lazy("cartitem-detail", args=[self.cart_item.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["id"], self.cart_item.id)
        self.assertEqual(response.data["data"]["product"]["id"], str(self.product.id))

    def test_cartitem_permissions_unauthenticated(self):
        """Test that unauthenticated users cannot access cart item endpoints (read-only)."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("cartitem-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        url = reverse_lazy("cartitem-detail", args=[self.cart_item.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cartitem_access_other_user(self):
        """Test that a user cannot access another user's cart items (read-only)."""
        self.client.force_authenticate(user=self.other_user)
        url = reverse_lazy("cartitem-detail", args=[self.cart_item.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
