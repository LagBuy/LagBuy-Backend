import datetime

from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient
from django.utils import timezone

from apps.coupons.models import Coupon
from apps.userAuth.models import CustomUser, Role
from apps.products.models import Product
from apps.profiles.models import UsersProfile, VendorsProfile, RidersProfile


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class CouponModelTest(TestCase):
    """Test cases for the Coupon model"""

    @classmethod
    def setUpTestData(cls):
        cls.seller = CustomUser.objects.create_user(
            email="seller@test.com",
            password="testpassword",
        )
        cls.sellerProfile = UsersProfile.objects.create(
            user=cls.seller,
            first_name="Seller",
            last_name="Test",
            phone_number="0909222002",
            gender='male',
            dob=datetime.date(2020, 7, 12),
        )
        cls.user_role, _ = Role.objects.get_or_create(name='user')
        cls.vendor_role, _ = Role.objects.get_or_create(name='vendor')
        cls.seller.roles.add(cls.user_role)
        cls.seller.roles.add(cls.vendor_role)

        cls.product1 = Product.objects.create(
            name="Test Product",
            price=1000,
            description="Test Description",
            stock_quantity=50,
            seller=cls.seller,
        )
        cls.coupon1 = Coupon.objects.create(
            code="testcoupon",
            discount_type="Fixed",
            discount_value=100,
            min_purchase_quantity=2,
            max_purchase_quantity=20,
            valid_from=timezone.now(),
            valid_to=(timezone.now() + timezone.timedelta(days=2)),
            usage_limit=5,
            seller=cls.seller,
        )
        cls.coupon1.products.add(cls.product1)
        cls.coupon2 = Coupon.objects.create(
            code="invalidcoupon",
            discount_value=100,
            valid_to=timezone.now(),
            seller=cls.seller,
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
        self.assertLessEqual(
            self.coupon1.valid_to, timezone.now() + timezone.timedelta(days=2)
        )
        self.assertEqual(self.coupon1.usage_limit, 5)
        self.assertEqual(self.coupon1.seller, self.seller)
        self.assertIn(self.product1, self.coupon1.products.all())
        # test code can be accessed from seller model
        self.assertIn(self.coupon1, self.seller.coupons.all())

    def test_coupon_str(self):
        """Test the string rep of the coupon"""
        self.assertEqual(
            str(self.coupon1), f"Coupon - {self.coupon1.code} by {self.seller}"
        )

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

        cls.user_role, _ = Role.objects.get_or_create(name='user')
        cls.vendor_role, _ = Role.objects.get_or_create(name='vendor')

        cls.buyer = CustomUser.objects.create_user(
            email="buyer@test.com",
            password="testpassword",
        )
        cls.buyerProfile = UsersProfile.objects.create(
            user=cls.buyer,
            first_name="Buyer",
            last_name="Test",
            phone_number="09092220021",
            gender='male',
            dob=datetime.date(2020, 7, 12),
        )
        cls.buyer.roles.add(cls.user_role)

        cls.seller = CustomUser.objects.create_user(
            email="seller@test.com",
            password="testpassword",
        )
        cls.sellerProfile = UsersProfile.objects.create(
            user=cls.seller,
            first_name="Seller",
            last_name="Test",
            phone_number="09092220022",
            gender='male',
            dob=datetime.date(2020, 7, 12),
        )
        cls.seller.roles.add(cls.user_role)
        cls.seller.roles.add(cls.vendor_role)

        cls.admin = CustomUser.objects.create_superuser(
            email="admin@test.com",
            password="password",
        )
        cls.adminProfile = UsersProfile.objects.create(
            user=cls.admin,
            first_name="Admin",
            last_name="Test",
            phone_number="0202222332",
            gender='male',
            dob=datetime.date(2020, 7, 12),
        )
        cls.admin.roles.add(cls.vendor_role)

        cls.product1 = Product.objects.create(
            name="Test Product",
            price=1000,
            description="Test Description",
            stock_quantity=50,
            seller=cls.seller,
        )
        cls.coupon1 = Coupon.objects.create(
            code="testcoupon",
            discount_type="Fixed",
            discount_value=100,
            min_purchase_quantity=2,
            max_purchase_quantity=20,
            valid_from=timezone.now(),
            valid_to=(timezone.now() + timezone.timedelta(days=2)),
            usage_limit=5,
            seller=cls.seller,
        )
        cls.coupon1.products.add(cls.product1)
        cls.product2 = Product.objects.create(
            name="Test Product 2",
            price=100,
            description="Test Description",
            stock_quantity=50,
            seller=cls.admin,
        )
        cls.coupon2 = Coupon.objects.create(
            code="admincoupon",
            discount_value=100,
            valid_to=(timezone.now() + timezone.timedelta(days=2)),
            seller=cls.admin,
        )
        cls.coupon2.products.add(cls.product2)

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
            "seller": self.buyer.id,  # test putting the wrong user
            "products": [self.product1.id],
        }
        response = self.client.post(url, data, format="json")
        data = response.data["data"]
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
        """Test to ensure a seller can only create coupon on a product they own"""
        url = reverse_lazy("coupon-list")
        data = {
            "code": "testcoupon3",
            "discount_value": 100.00,
            "valid_to": str(timezone.now() + timezone.timedelta(days=2)),
            "products": [self.product2.id],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # TODO: reevaluate how this feature works
    def test_create_unique_coupons_only(self):
        """Test to ensure each coupon a seller create is unique"""
        url = reverse_lazy("coupon-list")
        data = {
            "code": "testcoupon",
            "discount_value": 100.00,
            "valid_to": str(timezone.now() + timezone.timedelta(days=2)),
            "products": [self.product1.id],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # TODO: test this on the actual endpoint
    def test_create_coupon_with_invalid_dates(self):
        """Test to ensure a seller can only create a product they own"""
        url = reverse_lazy("coupon-list")
        data = {
            "code": "testcoupon3",
            "discount_value": 100.00,
            "valid_to": str(timezone.now()),
            "products": [self.product2.id],
        }
        data2 = {
            "code": "testcoupon3",
            "discount_value": 100.00,
            "valid_to": str(timezone.now() + timezone.timedelta(days=1)),
            "valid_from": str(timezone.now() + timezone.timedelta(days=2)),
            "products": [self.product2.id],
        }
        response = self.client.post(url, data, format="json")
        response2 = self.client.post(url, data2, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_seller_get_coupons(self):
        """Test retrieving all coupon under a seller"""
        url = reverse_lazy("coupon-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["code"], "testcoupon")

    def test_seller_get_coupon(self):
        """Test a seller can retrieve the full detail of their coupon"""
        url = reverse_lazy("coupon-detail", args=[self.coupon1.code])
        response = self.client.get(url)
        data = response.data["data"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data["code"], "testcoupon")
        self.assertEqual(data["discount_value"], "100.00")
        self.assertEqual(data["min_purchase_quantity"], 2)
        self.assertEqual(data["max_purchase_quantity"], 20)
        self.assertIn(self.product1.id, data["products"])

    def test_seller_get_wrong_coupon(self):
        """Test seller retreive with wrong coupon code"""
        url = reverse_lazy("coupon-detail", args=[self.coupon2.code])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_seller_update_coupon(self):
        """Test a seller can update their coupon"""
        url = reverse_lazy("coupon-detail", args=[self.coupon1.code])
        data = {
            # "code": "testcoupon10",
            "max_purchase_quantity": 50,
            "usage_limit": 10,
        }
        # TODO: use patch not put and test that unedited fields are not changed
        response = self.client.put(url, data, format="json")
        self.product1.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["max_purchase_quantity"], 50)
        self.assertEqual(response.data["data"]["usage_limit"], 10)

    def test_update_coupon_seller_with_wrong_seller(self):
        """Test a coupon seller can not be updated to a wrong seller"""
        url = reverse_lazy("coupon-detail", args=[self.coupon1.code])
        data = {
            "seller": self.buyer.id,  # test putting the wrong user
        }
        response = self.client.put(url, data, format="json")
        self.product1.refresh_from_db()
        self.assertEqual(response.data["data"]["seller"], self.seller.id)

    def test_update_coupon_seller_with_wrong_date(self):
        """Test a coupon seller can not be updated to a wrong seller"""
        url = reverse_lazy("coupon-detail", args=[self.coupon1.code])
        data = {
            "valid_to": str(timezone.now() + timezone.timedelta(days=1)),
            "valid_from": str(timezone.now() + timezone.timedelta(days=2)),
        }
        response = self.client.put(url, data, format="json")
        self.product1.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_seller_update_with_wrong_product(self):
        """Test a coupon cannot be updated with wrong product"""
        url = reverse_lazy("coupon-detail", args=[self.coupon1.code])
        data = {"products": [self.product2.id]}  # check for non seller product
        response = self.client.put(url, data, format="json")
        self.product1.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_seller_update_coupon_no_data(self):
        """Test update with no data provided"""
        url = reverse_lazy("coupon-detail", args=[self.coupon1.code])
        response = self.client.put(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_seller_delete_coupon(self):
        """Test deleting a coupon"""
        url = reverse_lazy("coupon-detail", args=[self.coupon1.code])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Coupon.objects.filter(code=self.coupon1.code).exists())

    def test_update_wrong_coupon(self):
        """Test a wrong owner cannot update another seller coupon"""
        url = reverse_lazy("coupon-detail", args=[self.coupon1.code])
        self.client.force_authenticate(user=self.buyer)
        data = {
            "max_purchase_quantity": 50,
            "usage_limit": 10,
        }
        response = self.client.put(url, data, format="json")
        self.product1.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_wrong_coupon(self):
        """Test a wrong owner cannot delete another seller coupon"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("coupon-detail", args=[self.coupon1.code])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Coupon.objects.filter(code=self.coupon1.code).exists())

    def test_no_seller_coupon(self):
        """Test the response when a seller has not created a coupon"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("coupon-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 0)
        self.assertEqual(response.data["data"], [])

    def test_admin_get_all_coupons(self):
        """Test an admin can see all coupon"""
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("admin-coupons-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

    def test_admin_get_seller_coupon(self):
        """Test an admin can retrieve a specific coupon for any seller"""
        self.client.force_authenticate(user=self.admin)
        url = reverse_lazy("admin-coupon-detail", args=[self.coupon1.code])
        response = self.client.get(url)
        data = response.data["data"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data["code"], "testcoupon")
        self.assertEqual(data["discount_value"], "100.00")
        self.assertEqual(data["min_purchase_quantity"], 2)
        self.assertEqual(data["max_purchase_quantity"], 20)
        self.assertIn(self.product1.id, data["products"])

    def test_get_coupon_status(self):
        """Test verifying the coupon status"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("verify-coupon")
        data = {"code": "testcoupon", "product_id": self.product1.id, "quantity": 5}
        response = self.client.post(url, data, format="json")
        data = response.data["data"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data["code"], "testcoupon")
        self.assertEqual(data["discount_value"], "100.00")
        self.assertEqual(data["discount_type"], "Fixed")
        self.assertEqual(data.get("min_purchase_quantity", None), None)
        self.assertEqual(data.get("max_purchase_quantity", None), None)
        self.assertEqual(data.get("products", None), None)

    def test_get_wrong_coupon(self):
        """Test the response when a wrong coupon is requested for verification"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("verify-coupon")
        data = {"code": "couponnotexist", "product_id": self.product1.id, "quantity": 5}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_coupon_with_incomplete_data(self):
        """Test the response when a wrong coupon is requested"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("verify-coupon")
        data = {
            "code": "testcoupon",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_coupon_with_wrong_product_id(self):
        """Test the response when a coupon with wrong product is requested for verification"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("verify-coupon")
        data = {"code": "testcoupon", "product_id": "kdh38923jlh2323", "quantity": 5}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_coupon_with_wrong_seller_product(self):
        """Test the response when a wrong coupon is requested for verification"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("verify-coupon")
        data = {"code": "testcoupon", "product_id": self.product2.id, "quantity": 5}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_coupon_with_wrong_min_quatitiy(self):
        """Test the response when a wrong coupon is requested for verification"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("verify-coupon")
        data = {"code": "testcoupon", "product_id": self.product1.id, "quantity": 1}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_coupon_with_wrong_max_quatitiy(self):
        """Test the response when a wrong coupon is requested for verification"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse_lazy("verify-coupon")
        data = {"code": "testcoupon", "product_id": self.product1.id, "quantity": 100}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
