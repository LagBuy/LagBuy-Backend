from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient
from django.utils import timezone

from apps.coupons.models import Coupon
from apps.users.models import CustomUser
from apps.products.models import Product


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class CouponModelTest(TestCase):
    """Test cases for the Coupon model"""

    @classmethod
    def setUpTestData(cls):
        cls.seller = CustomUser.objects.create_user(
            username="testseller",
            password="testpassword",
            email="seller@test.com",
            first_name="Seller",
            last_name="Test",
            phone_number="0909222002",
            role="seller",
        )
        cls.product1 = Product.objects.create(
            name = "Test Product",
            price = 1000,
            images=[],
            description = "Test Description",
            stock_quantity = 50,
            seller=cls.seller,
        )
        cls.coupon1 = Coupon.objects.create(
            code="testcoupon",
            discount_type = "Fixed",
            discount_value = 100,
            min_purchase_quantity = 2,
            max_purchase_quantity = 20,
            valid_from = timezone.now(),
            valid_to = (timezone.now() + timezone.timedelta(days=2)),
            usage_limit = 5,
            seller = cls.seller,
        )
        cls.coupon1.products.add(cls.product1)
        cls.coupon2 = Coupon.objects.create(
            code="invalidcoupon",
            discount_value = 100,
            valid_to = timezone.now(),
            seller = cls.seller,
        )
        cls.coupon2.products.add(cls.product1)
    
    def test_coupon_creation(self):
        """Test that the coupon was created successfully using the model"""
        self.assertEqual(self.coupon1.code, "testcoupon")
        self.assertEqual(self.coupon1.discount_type, "Fixed")
        self.assertEqual(self.coupon1.discount_value, 100)
        self.assertEqual(self.coupon1.min_purchase_quantity, 2)
        self.assertEqual(self.coupon1.max_purchase_quantity, 20)
        self.assertLessEqual(self.coupon1.valid_from, timezone.now())
        self.assertLessEqual(self.coupon1.valid_to, timezone.now() + timezone.timedelta(days=2))
        self.assertEqual(self.coupon1.usage_limit, 5)
        self.assertEqual(self.coupon1.seller, self.seller)
        self.assertIn(self.product1, self.coupon1.products.all())
        # test code can be accessed from seller model
        self.assertIn(self.coupon1, self.seller.coupons.all())
    
    def test_coupon_str(self):
        """Test the string rep of the coupon"""
        self.assertEqual(str(self.coupon1), f"Coupon - {self.coupon1.code} by {self.seller}")
    
    def test_coupon_status(self):
        """Test the status property of the coupon"""
        self.assertTrue(self.coupon1.status)
        self.assertFalse(self.coupon2.status)


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class CouponAPITest(TestCase):
    """Test cases for the Coupon API views"""
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.buyer = CustomUser.objects.create_user(
            username="testbuyer",
            password="testpassword",
            email="buyer@test.com",
            first_name="Buyer",
            last_name="Test",
            phone_number="0909222002",
        )
        cls.seller = CustomUser.objects.create_user(
            username="testseller",
            password="testpassword",
            email="seller@test.com",
            first_name="Seller",
            last_name="Test",
            phone_number="0909222002",
            role="seller",
        )
        cls.admin = CustomUser.objects.create_superuser(
            username = "admin",
            password = "password",
            email = "admin@test.com",
            first_name = "Admin",
            last_name = "Test",
            phone_number = "0202222332",
        )
        cls.product1 = Product.objects.create(
            name = "Test Product",
            price = 1000,
            images=[],
            description = "Test Description",
            stock_quantity = 50,
            seller=cls.seller,
        )
        cls.coupon1 = Coupon.objects.create(
            code="testcoupon",
            discount_type = "Fixed",
            discount_value = 100,
            min_purchase_quantity = 2,
            max_purchase_quantity = 20,
            valid_from = timezone.now(),
            valid_to = (timezone.now() + timezone.timedelta(days=2)),
            usage_limit = 5,
            seller = cls.seller,
        )
        cls.coupon1.products.add(cls.product1)
        cls.product2 = Product.objects.create(
            name = "Test Product 2",
            price = 100,
            images=[],
            description = "Test Description",
            stock_quantity = 50,
            seller=cls.admin,
        )
        
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.seller)

    def test_create_coupon(self):
        """Test creating a coupon"""
        url = reverse_lazy("coupon-list")
        data = {
            "code": "testcoupon2",
            "discount_type": "FIXED",
            "discount_value": 100.00,
            "min_purchase_quantity": 2,
            "max_purchase_quantity": 20,
            "valid_from": str(timezone.now()),
            "valid_to": str(timezone.now() + timezone.timedelta(days=2)),
            "usage_limit": 5,
            "seller": self.buyer.id, # test putting the wrong user
            "products": [self.product1.id]
            }
        response = self.client.post(url, data, format="json")
        data = response.data['data']
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(data["code"], "testcoupon2")
        self.assertEqual(data["discount_type"], "FIXED")
        self.assertEqual(data["discount_value"], "100.00")
        self.assertEqual(data["min_purchase_quantity"], 2)
        self.assertEqual(data["max_purchase_quantity"], 20)
        self.assertEqual(data["usage_limit"], 5)
        self.assertEqual(data["seller"], self.seller.id)
        self.assertTrue(data["status"])
        self.assertIn(self.product1.id, data["products"])
        self.assertNotEqual(data["seller"], self.buyer.id)
    
    def test_create_coupon_with_wrong_product(self):
        """Test to ensure a seller can only create a product they own"""
        url = reverse_lazy("coupon-list")
        data = {
            "code": "testcoupon3",
            "discount_value": 100.00,
            "products": [self.product2.id]
            }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_coupon_with_invalid_date(self):
        """Test to ensure a seller can only create a product they own"""
        url = reverse_lazy("coupon-list")
        data = {
            "code": "testcoupon3",
            "discount_value": 100.00,
            "valid_to": str(timezone.now()),
            "products": [self.product2.id]
            }
        data2 = {
            "code": "testcoupon3",
            "discount_value": 100.00,
            "valid_to": str(timezone.now() + timezone.timedelta(days=1)),
            "valid_from": str(timezone.now() + timezone.timedelta(days=2)),
            "products": [self.product2.id]
            }
        response = self.client.post(url, data, format="json")
        response2 = self.client.post(url, data2, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        

    def test_seller_get_coupon(self):
        """Test retrieving all coupon under a seller"""
        url = reverse_lazy("coupon-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data['data'][0]['code'], 'testcoupon')
    

