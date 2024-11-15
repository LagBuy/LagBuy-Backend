from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import Product
from apps.users.models import CustomUser

from .models import Review


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class ReviewAPITest(TestCase):
    """Test cases for the Review API views."""

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
        cls.other_user = CustomUser.objects.create_user(
            username="other_user",
            password="password",
            email="other_user@example.com",
            first_name="Other",
            last_name="User",
            phone_number="0987654321",
        )
        cls.product = Product.objects.create(
            name="Test Product",
            price=100.0,
            images=[],
            description="Test Description",
            stock_quantity=10,
            seller=cls.user,
        )
        cls.review = Review.objects.create(
            product=cls.product,
            buyer=cls.user,
            rating=5,
            comment="Great product!",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_review(self):
        """Test creating a review."""
        # Delete the existing review to avoid duplicate error
        Review.objects.filter(id=self.review.id).delete()

        url = reverse_lazy("review-list")
        data = {
            "product": self.product.id,
            "rating": 4,
            "comment": "Good product!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["buyer"], self.user.id)
        self.assertEqual(response.data["product"], self.product.id)
        self.assertEqual(response.data["rating"], 4)
        self.assertEqual(response.data["comment"], "Good product!")

    def test_create_duplicate_review(self):
        """Test creating a duplicate review should fail."""
        url = reverse_lazy("review-list")
        data = {
            "product": self.product.id,
            "rating": 4,
            "comment": "Good product!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertEqual(
            response.data["non_field_errors"][0],
            "You have already reviewed this product.",
        )

    def test_get_reviews(self):
        """Test retrieving all reviews for a product."""
        url = reverse_lazy("review-list")
        response = self.client.get(url, {"product_id": self.product.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(self.review.id))

    def test_get_review(self):
        """Test retrieving a single review."""
        url = reverse_lazy("review-detail", args=[self.review.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.review.id))

    def test_update_review(self):
        """Test updating a review."""
        url = reverse_lazy("review-detail", args=[self.review.id])
        data = {
            "rating": 3,
            "comment": "Average product.",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rating"], 3)
        self.assertEqual(response.data["comment"], "Average product.")

    def test_update_review_with_product(self):
        """Test updating a review with product should return bad request."""
        url = reverse_lazy("review-detail", args=[self.review.id])
        data = {
            "product": self.product.id,
            "rating": 3,
            "comment": "Average product.",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_review(self):
        """Test deleting a review."""
        url = reverse_lazy("review-detail", args=[self.review.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Review.objects.filter(id=self.review.id).exists())

    def test_create_review_unauthenticated(self):
        """Test that unauthenticated users cannot create a review."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("review-list")
        data = {
            "product": self.product.id,
            "rating": 4,
            "comment": "Good product!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_review_unauthenticated(self):
        """Test that unauthenticated users cannot update a review."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("review-detail", args=[self.review.id])
        data = {
            "rating": 3,
            "comment": "Average product.",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_review_unauthenticated(self):
        """Test that unauthenticated users cannot delete a review."""
        self.client.force_authenticate(user=None)
        url = reverse_lazy("review-detail", args=[self.review.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_review_not_owner(self):
        """Test that users cannot update a review they do not own."""
        self.client.force_authenticate(user=self.other_user)
        url = reverse_lazy("review-detail", args=[self.review.id])
        data = {
            "rating": 3,
            "comment": "Average product.",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_review_not_owner(self):
        """Test that users cannot delete a review they do not own."""
        self.client.force_authenticate(user=self.other_user)
        url = reverse_lazy("review-detail", args=[self.review.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
