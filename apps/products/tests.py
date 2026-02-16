import datetime

from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.profiles.models import UsersProfile, VendorsProfile
from apps.userAuth.models import CustomUser, Role


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class CategoryAPITest(TestCase):
    """Test cases for the Category API views."""

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        cls.user_role, _ = Role.objects.get_or_create(name='user')
        cls.vendor_role, _ = Role.objects.get_or_create(name='vendor')

        cls.admin = CustomUser.objects.create_superuser(
            email="admin@example.com",
            password="password",
        )
        cls.admin.roles.add(cls.user_role)

        cls.user = CustomUser.objects.create_user(
            email="user@example.com",
            password="password",
        )
        cls.user.roles.add(cls.user_role)

        cls.vendor = CustomUser.objects.create_user(
            email="vendor@example.com",
            password="password",
        )
        cls.vendor.roles.add(cls.vendor_role)

        cls.category = Category.objects.create(
            name="Test Category",
            description="Test Description",
        )

    def setUp(self):
        self.client = APIClient()

    # def test_admin_can_create_category(self):
    #     self.client.force_authenticate(user=self.admin)
    #     url = reverse_lazy("category-list")
    #     data = {"name": "New Category", "description": "New Desc"}
    #     response = self.client.post(url, data, format="json")
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #     self.assertEqual(response.data["data"]["name"], "New Category")

    def test_vendor_can_create_category(self):
        self.client.force_authenticate(user=self.vendor)
        url = reverse_lazy("category-list")
        data = {"name": "New Category", "description": "New Desc"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["name"], "New Category")

    def test_non_admin_cannot_create_category(self):
        self.client.force_authenticate(user=self.user)
        url = reverse_lazy("category-list")
        data = {"name": "Fail Category", "description": "Should Fail"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_categories(self):
        self.client.force_authenticate(user=self.user)
        url = reverse_lazy("category-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("data" in response.data)
        self.assertEqual(response.data["data"][0]["name"], "Test Category")

    def test_admin_can_update_category(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("category-detail", args=[self.category.id])
        data = {"name": "Updated Category", "description": "Updated Desc"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "Updated Category")

    def test_non_admin_cannot_update_category(self):
        self.client.force_authenticate(user=self.user)
        url = reverse_lazy("category-detail", args=[self.category.id])
        data = {"name": "Should Not Update", "description": "No"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_category(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("category-detail", args=[self.category.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(id=self.category.id).exists())

    def test_non_admin_cannot_delete_category(self):
        self.client.force_authenticate(user=self.user)
        url = reverse_lazy("category-detail", args=[self.category.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # def test_unauthenticated_cannot_access_categories(self):
    #     url = reverse_lazy("category-list")
    #     response = self.client.get(url)
    #     self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class ProductAPITest(TestCase):
    """Test cases for the Product API views."""

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        cls.user_role, _ = Role.objects.get_or_create(name='user')
        cls.vendor_role, _ = Role.objects.get_or_create(name='vendor')

        cls.seller = CustomUser.objects.create_user(
            email="seller@example.com",
            password="password",
        )
        UsersProfile.objects.create(
            user=cls.seller,
            first_name="Seller",
            last_name="User",
            phone_number="09876543210"
        )
        VendorsProfile.objects.create(
            user=cls.seller,
            business_name="Seller Business",
            business_address="123 Seller St",
            business_location_city="Seller City",
            business_location_state="Seller State",
            is_verified=True,
        )
        cls.seller.roles.add(cls.user_role)
        cls.seller.roles.add(cls.vendor_role)

        cls.buyer = CustomUser.objects.create_user(
            email="buyer@example.com",
            password="password",
        )
        cls.buyer.roles.add(cls.user_role)
        UsersProfile.objects.create(
            user=cls.buyer,
            first_name="Buyer",
            last_name="User",
            phone_number="09876543211"
        )

        cls.category = Category.objects.create(
            name="Test Category",
            description="Test Description",
        )
        cls.product = Product.objects.create(
            name="Test Product",
            price=100.0,
            description="Test Description",
            stock_quantity=10,
            seller=cls.seller,
        )
        cls.product.categories.add(cls.category)

    def setUp(self):
        self.client = APIClient()

    def test_seller_can_create_product(self):
        self.client.force_authenticate(user=self.seller)
        url = reverse_lazy("product-list")
        data = {
            "name": "New Product",
            "price": 150.0,
            "description": "New Description",
            "stock_quantity": 20,
            "categories": [self.category.name],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["name"], "New Product")

    def test_non_seller_cannot_create_product(self):
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("product-list")
        data = {
            "name": "Fail Product",
            "price": 10.0,
            "images": [],
            "description": "Should Fail",
            "stock_quantity": 1,
            "categories": [self.category.name],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_products(self):
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("product-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("data" in response.data)
        self.assertEqual(response.data["data"][0]["name"], "Test Product")
    
    def test_filter_product_by_location(self):
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("product-list") + "?city=Seller City&state=Seller State"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("data" in response.data)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["name"], "Test Product")
    
    def test_filter_product_by_vendor(self):
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("product-list") + "?vendor=Seller Business"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("data" in response.data)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["name"], "Test Product")
    
    def test_filter_product_by_price_range(self):
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("product-list") + "?min_price=50&max_price=150"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("data" in response.data)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["name"], "Test Product")
    
    def test_filter_product_no_match(self):
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("product-list") + "?city=Nonexistent City"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("data" in response.data)
        self.assertEqual(len(response.data["data"]), 0)
    
    def test_filter_product_by_category(self):
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("product-list") + "?categories=Test Category"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("data" in response.data)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["name"], "Test Product")
    
    def test_get_product_owned_by_seller(self):
        self.client.force_authenticate(user=self.seller)
        url = reverse_lazy("product-list") + f"?vendor_id={self.seller.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("data" in response.data)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["name"], "Test Product")
    
    def test_return_seller_short_address_in_product_list(self):
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("product-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("data" in response.data)
        self.assertEqual(response.data["data"][0]["shop_location"], "Seller City, Seller State")

    def test_get_product_detail(self):
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("product-detail", args=[self.product.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["name"], "Test Product")
        self.assertEqual(response.data["data"]["stock_quantity"], 10)

    def test_seller_can_update_product(self):
        self.client.force_authenticate(user=self.seller)
        url = reverse_lazy("product-detail", args=[self.product.id])
        data = {
            "name": "Updated Product",
            "price": 200.0,
            "description": "Updated Description",
            "stock_quantity": 15,
            "categories": [self.category.name],
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Updated Product")
        self.assertEqual(self.product.price, 200.0)
        self.assertEqual(self.product.stock_quantity, 15)

    def test_non_seller_cannot_update_product(self):
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("product-detail", args=[self.product.id])
        data = {"name": "Should Not Update"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_seller_can_delete_product(self):
        self.client.force_authenticate(user=self.seller)
        url = reverse_lazy("product-detail", args=[self.product.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())

    def test_non_seller_cannot_delete_product(self):
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("product-detail", args=[self.product.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_product_stock(self):
        self.client.force_authenticate(user=self.seller)
        url = reverse_lazy("product-update-stock", args=[self.product.id])
        data = {"stock_quantity": 15}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 15)

    def test_update_product_stock_invalid(self):
        self.client.force_authenticate(user=self.seller)
        url = reverse_lazy("product-update-stock", args=[self.product.id])
        data = {"stock_quantity": -5}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_product_added_to_user_viewed_products(self):
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("product-detail", args=[self.product.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.buyer.refresh_from_db()
        self.assertIn(self.product, self.buyer.user_profile.viewed_products.all())
    
    def test_get_viewed_products(self):
        self.client.force_authenticate(user=self.buyer)
        # Simulate viewing the product
        url = reverse_lazy("product-detail", args=[self.product.id])
        self.client.get(url)
        # Test the viewed products endpoint
        url = reverse_lazy("viewed-products-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("data" in response.data)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["name"], "Test Product")
