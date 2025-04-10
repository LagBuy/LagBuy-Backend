from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.users.models import CustomUser


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class CategoryModelTest(TestCase):
    """Test cases for the Category model."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = CustomUser.objects.create_superuser(
            username="admin",
            password="password",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            phone_number="1122334455",
        )
        cls.category = Category.objects.create(
            name="Test Category",
            description="Test Description",
        )

    def test_category_creation(self):
        """Test that a category is created successfully."""
        self.assertEqual(self.category.name, "Test Category")
        self.assertEqual(self.category.description, "Test Description")

    def test_category_str(self):
        """Test the string representation of the category."""
        self.assertEqual(str(self.category), "Test Category")


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class CategoryAPITest(TestCase):
    """Test cases for the Category API views."""

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.admin = CustomUser.objects.create_superuser(
            username="admin",
            password="password",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            phone_number="1122334455",
        )
        cls.category = Category.objects.create(
            name="Test Category",
            description="Test Description",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_create_category(self):
        """Test creating a category."""
        url = reverse_lazy("category-list")
        data = {
            "name": "New Category",
            "description": "New Description",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Category")
        self.assertEqual(response.data["description"], "New Description")

    def test_get_categories(self):
        """Test retrieving all categories."""
        url = reverse_lazy("category-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Test Category")

    def test_update_category(self):
        """Test updating a category."""
        url = reverse_lazy("category-detail", args=[self.category.id])
        data = {
            "name": "Updated Category",
            "description": "Updated Description",
        }
        response = self.client.put(url, data, format="json")
        self.category.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.category.name, "Updated Category")
        self.assertEqual(self.category.description, "Updated Description")

    def test_delete_category(self):
        """Test deleting a category."""
        url = reverse_lazy("category-detail", args=[self.category.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(id=self.category.id).exists())


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class ProductModelTest(TestCase):
    """Test cases for the Product model."""

    @classmethod
    def setUpTestData(cls):
        cls.seller = CustomUser.objects.create_user(
            username="seller",
            password="password",
            email="seller@example.com",
            first_name="Seller",
            last_name="User",
            phone_number="0987654321",
            role="seller",
        )
        cls.category = Category.objects.create(
            name="Test Category",
            description="Test Description",
        )
        cls.product = Product.objects.create(
            name="Test Product",
            price=100.0,
            images=[],
            description="Test Description",
            stock_quantity=10,
            seller=cls.seller,
        )
        cls.product.categories.add(cls.category)

    def test_product_creation(self):
        """Test that a product is created successfully."""
        self.assertEqual(self.product.name, "Test Product")
        self.assertEqual(self.product.price, 100.0)
        self.assertEqual(self.product.description, "Test Description")
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertEqual(self.product.seller, self.seller)
        self.assertIn(self.category, self.product.categories.all())

    def test_product_str(self):
        """Test the string representation of the product."""
        self.assertEqual(str(self.product), f"Test Product by {self.seller}")


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class ProductAPITest(TestCase):
    """Test cases for the Product API views."""

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
        cls.category = Category.objects.create(
            name="Test Category",
            description="Test Description",
        )
        cls.product = Product.objects.create(
            name="Test Product",
            price=100.0,
            images=[],
            description="Test Description",
            stock_quantity=10,
            seller=cls.seller,
        )
        cls.product.categories.add(cls.category)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.seller)

    def test_create_product(self):
        """Test creating a product."""
        url = reverse_lazy("product-list")
        data = {
            "name": "New Product",
            "price": 150.0,
            "images": [],
            "description": "New Description",
            "stock_quantity": 20,
            "categories": [str(self.category.id)],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Product")
        self.assertEqual(response.data["price"], "150.00")
        self.assertEqual(response.data["description"], "New Description")
        self.assertEqual(response.data["stock_quantity"], 20)
        self.assertEqual(response.data["seller"], f"Seller User [{self.seller.email}]")

    def test_get_products(self):
        """Test retrieving all products."""
        url = reverse_lazy("product-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Test Product")

    def test_get_product(self):
        """Test retrieving a specific product."""
        url = reverse_lazy("product-detail", args=[self.product.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Product")

    def test_update_product(self):
        """Test updating a product."""
        url = reverse_lazy("product-detail", args=[self.product.id])
        data = {
            "name": "Updated Product",
            "price": 200.0,
            "description": "Updated Description",
            "stock_quantity": 15,
            "categories": [str(self.category.id)],
        }
        response = self.client.patch(url, data, format="json")
        self.product.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.product.name, "Updated Product")
        self.assertEqual(self.product.price, 200.0)
        self.assertEqual(self.product.description, "Updated Description")
        self.assertEqual(self.product.stock_quantity, 15)

    def test_delete_product(self):
        """Test deleting a product."""
        url = reverse_lazy("product-detail", args=[self.product.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())

    def test_update_product_stock(self):
        """Test updating the stock of a product."""
        url = reverse_lazy("product-update-stock", args=[self.product.id])
        data = {"quantity": 5}
        response = self.client.post(url, data, format="json")
        self.product.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.product.stock_quantity, 15)

    def test_cannot_update_stock_below_zero(self):
        """Test that stock cannot be updated below zero."""
        url = reverse_lazy("product-update-stock", args=[self.product.id])
        data = {"quantity": -20}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient stock.", str(response.data))
