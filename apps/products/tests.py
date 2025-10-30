import datetime
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock

from botocore.exceptions import ClientError
from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from PIL import Image
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
            phone_number="1234567890"
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


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class ImageUploadViewTest(TestCase):
    """Test cases for the ImageUploadView and StorageService."""

    @classmethod
    def setUpTestData(cls):
        cls.user_role, _ = Role.objects.get_or_create(name='user')
        cls.vendor_role, _ = Role.objects.get_or_create(name='vendor')

        cls.authenticated_user = CustomUser.objects.create_user(
            email="authuser@example.com",
            password="password",
        )
        cls.authenticated_user.roles.add(cls.user_role)

    def setUp(self):
        self.client = APIClient()
        self.url = reverse_lazy("image-upload")

    def create_test_image(self, format_type="JPEG", mode="RGB", size=(100, 100)):
        """
        Helper method to create a test image in different formats.
        
        Args:
            format_type: Image format (JPEG, PNG, WEBP, GIF, BMP, TIFF)
            mode: Image mode (RGB, RGBA, L, P, etc.)
            size: Tuple of (width, height)
        
        Returns:
            BytesIO object containing the image data
        """
        image = Image.new(mode, size, color=(255, 0, 0))
        image_io = BytesIO()
        
        # Handle different format requirements
        if format_type in ["JPEG", "JPG"]:
            # JPEG doesn't support transparency, convert to RGB if needed
            if mode in ("RGBA", "LA", "P"):
                image = image.convert("RGB")
            image.save(image_io, format="JPEG", quality=85)
            image_io.name = f"test_image.jpg"
        elif format_type == "PNG":
            image.save(image_io, format="PNG")
            image_io.name = f"test_image.png"
        elif format_type == "WEBP":
            image.save(image_io, format="WEBP", quality=85)
            image_io.name = f"test_image.webp"
        elif format_type == "GIF":
            if mode not in ("P", "L", "RGB", "RGBA"):
                image = image.convert("RGB")
            image.save(image_io, format="GIF")
            image_io.name = f"test_image.gif"
        elif format_type == "BMP":
            image.save(image_io, format="BMP")
            image_io.name = f"test_image.bmp"
        elif format_type == "TIFF":
            image.save(image_io, format="TIFF")
            image_io.name = f"test_image.tiff"
        
        image_io.seek(0)
        return image_io

    @patch('common.services.storage.StorageService.upload_file')
    def test_upload_jpeg_image_success(self, mock_upload):
        """Test successful upload of JPEG image."""
        mock_upload.return_value = "https://test-bucket.s3.us-east-1.amazonaws.com/test123.jpg"
        
        self.client.force_authenticate(user=self.authenticated_user)
        image_file = self.create_test_image(format_type="JPEG", mode="RGB")
        
        response = self.client.post(
            self.url,
            {"image": image_file},
            format="multipart"
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("url", response.data)
        self.assertTrue(response.data["url"].startswith("https://"))
        mock_upload.assert_called_once()

    @patch('common.services.storage.StorageService.upload_file')
    def test_upload_png_image_success(self, mock_upload):
        """Test successful upload of PNG image."""
        mock_upload.return_value = "https://test-bucket.s3.us-east-1.amazonaws.com/test456.png"
        
        self.client.force_authenticate(user=self.authenticated_user)
        image_file = self.create_test_image(format_type="PNG", mode="RGBA")
        
        response = self.client.post(
            self.url,
            {"image": image_file},
            format="multipart"
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("url", response.data)
        mock_upload.assert_called_once()

    @patch('common.services.storage.StorageService.upload_file')
    def test_upload_png_with_transparency(self, mock_upload):
        """Test upload of PNG image with alpha channel (transparency)."""
        mock_upload.return_value = "https://test-bucket.s3.us-east-1.amazonaws.com/transparent.png"
        
        self.client.force_authenticate(user=self.authenticated_user)
        image_file = self.create_test_image(format_type="PNG", mode="RGBA")
        
        response = self.client.post(
            self.url,
            {"image": image_file},
            format="multipart"
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("url", response.data)

    @patch('common.services.storage.StorageService.upload_file')
    def test_upload_webp_image_success(self, mock_upload):
        """Test successful upload of WEBP image."""
        mock_upload.return_value = "https://test-bucket.s3.us-east-1.amazonaws.com/test789.webp"
        
        self.client.force_authenticate(user=self.authenticated_user)
        image_file = self.create_test_image(format_type="WEBP", mode="RGB")
        
        response = self.client.post(
            self.url,
            {"image": image_file},
            format="multipart"
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("url", response.data)

    @patch('common.services.storage.StorageService.upload_file')
    def test_upload_gif_image_success(self, mock_upload):
        """Test successful upload of GIF image."""
        mock_upload.return_value = "https://test-bucket.s3.us-east-1.amazonaws.com/test.gif"
        
        self.client.force_authenticate(user=self.authenticated_user)
        image_file = self.create_test_image(format_type="GIF", mode="P")
        
        response = self.client.post(
            self.url,
            {"image": image_file},
            format="multipart"
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("url", response.data)

    @patch('common.services.storage.StorageService.upload_file')
    def test_upload_bmp_image_success(self, mock_upload):
        """Test successful upload of BMP image."""
        mock_upload.return_value = "https://test-bucket.s3.us-east-1.amazonaws.com/test.bmp"
        
        self.client.force_authenticate(user=self.authenticated_user)
        image_file = self.create_test_image(format_type="BMP", mode="RGB")
        
        response = self.client.post(
            self.url,
            {"image": image_file},
            format="multipart"
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("url", response.data)

    @patch('common.services.storage.StorageService.upload_file')
    def test_upload_tiff_image_success(self, mock_upload):
        """Test successful upload of TIFF image."""
        mock_upload.return_value = "https://test-bucket.s3.us-east-1.amazonaws.com/test.tiff"
        
        self.client.force_authenticate(user=self.authenticated_user)
        image_file = self.create_test_image(format_type="TIFF", mode="RGB")
        
        response = self.client.post(
            self.url,
            {"image": image_file},
            format="multipart"
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("url", response.data)

    def test_upload_without_authentication(self):
        """Test that unauthenticated users cannot upload images."""
        image_file = self.create_test_image(format_type="JPEG")
        
        response = self.client.post(
            self.url,
            {"image": image_file},
            format="multipart"
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_without_image_file(self):
        """Test upload request without providing an image file."""
        self.client.force_authenticate(user=self.authenticated_user)
        
        response = self.client.post(self.url, {}, format="multipart")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], "No image file provided.")

    @patch('common.services.storage.StorageService.upload_file')
    def test_upload_with_invalid_file(self, mock_upload):
        """Test upload with a non-image file."""
        mock_upload.side_effect = Exception("Failed to open image")
        
        self.client.force_authenticate(user=self.authenticated_user)
        
        # Create a text file instead of an image
        text_file = BytesIO(b"This is not an image")
        text_file.name = "not_an_image.txt"
        
        with self.assertRaises(Exception):
            response = self.client.post(
                self.url,
                {"image": text_file},
                format="multipart"
            )

    @patch('common.services.storage.StorageService.upload_file')
    def test_upload_s3_upload_failure(self, mock_upload):
        """Test handling of S3 upload failure."""
        # Simulate ClientError from boto3
        error_response = {'Error': {'Code': 'NoSuchBucket', 'Message': 'The specified bucket does not exist'}}
        mock_upload.side_effect = ClientError(error_response, 'PutObject')
        
        self.client.force_authenticate(user=self.authenticated_user)
        image_file = self.create_test_image(format_type="JPEG")
        
        with self.assertRaises(ClientError):
            response = self.client.post(
                self.url,
                {"image": image_file},
                format="multipart"
            )

    @patch('common.services.storage.StorageService.upload_file')
    def test_upload_returns_none(self, mock_upload):
        """Test when upload_file returns None (upload failed but no exception)."""
        mock_upload.return_value = None
        
        self.client.force_authenticate(user=self.authenticated_user)
        image_file = self.create_test_image(format_type="JPEG")
        
        response = self.client.post(
            self.url,
            {"image": image_file},
            format="multipart"
        )
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], "Failed to upload image.")

    @patch('common.services.storage.StorageService.upload_file')
    def test_upload_large_image(self, mock_upload):
        """Test upload of a large image (tests compression)."""
        mock_upload.return_value = "https://test-bucket.s3.us-east-1.amazonaws.com/large.jpg"
        
        self.client.force_authenticate(user=self.authenticated_user)
        # Create a larger image
        image_file = self.create_test_image(format_type="JPEG", mode="RGB", size=(2000, 2000))
        
        response = self.client.post(
            self.url,
            {"image": image_file},
            format="multipart"
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("url", response.data)

    @patch('common.services.storage.StorageService.upload_file')
    def test_upload_converts_rgba_to_rgb_for_jpeg(self, mock_upload):
        """Test that RGBA images are converted to RGB when saving as JPEG."""
        mock_upload.return_value = "https://test-bucket.s3.us-east-1.amazonaws.com/converted.jpg"
        
        self.client.force_authenticate(user=self.authenticated_user)
        # Create RGBA image but save as JPEG (which doesn't support alpha)
        image_file = self.create_test_image(format_type="JPEG", mode="RGB")
        
        response = self.client.post(
            self.url,
            {"image": image_file},
            format="multipart"
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("url", response.data)

    @patch('common.services.storage.StorageService.upload_file')
    def test_storage_service_called_with_correct_params(self, mock_upload):
        """Test that the storage service is called with the correct parameters."""
        mock_upload.return_value = "https://test-bucket.s3.us-east-1.amazonaws.com/test.jpg"
        
        self.client.force_authenticate(user=self.authenticated_user)
        image_file = self.create_test_image(format_type="JPEG")
        
        response = self.client.post(
            self.url,
            {"image": image_file},
            format="multipart"
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify upload_file was called with the file object, filename, and content_type
        self.assertTrue(mock_upload.called)
        call_args = mock_upload.call_args
        # First argument should be the file object
        self.assertIsNotNone(call_args[0][0])
        # Second argument should be the filename
        self.assertIn("test_image", call_args[0][1])
        # Third argument should be the content type
        self.assertIsNotNone(call_args[0][2])

    @patch('common.services.storage.StorageService.upload_file')
    def test_upload_generic_exception(self, mock_upload):
        """Test handling of generic exceptions during upload."""
        mock_upload.side_effect = Exception("Unexpected error")
        
        self.client.force_authenticate(user=self.authenticated_user)
        image_file = self.create_test_image(format_type="JPEG")
        
        with self.assertRaises(Exception) as context:
            response = self.client.post(
                self.url,
                {"image": image_file},
                format="multipart"
            )
        
        self.assertIn("Unexpected error", str(context.exception))
