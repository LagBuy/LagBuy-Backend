from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from django.utils import timezone
from django.core.mail import outbox
import datetime

from apps.userAuth.models import CustomUser, Role
from .models import VendorsProfile, UsersProfile, RidersProfile


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class ProfileModelsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(
            email="testuser@gmail.com",
            password="user1234",
        )
        cls.userProfile = UsersProfile.objects.create(
            user=cls.user,
            first_name="test",
            last_name="user",
            phone_number="08012345678",
            gender="male",
            dob=datetime.date(2020, 7, 12),
        )
        cls.vendorProfile = VendorsProfile.objects.create(
            user=cls.user,
            business_name="Test business",
            business_location_city="Test city",
            business_location_state="Test state",
        )
        cls.riderProfile = RidersProfile.objects.create(
            user=cls.user,
            phone_number2="08012345678",
            nin="123456789",
            next_of_kin="test person",
            motorcycle_type="bike",
            motorcycle_brand="Honda",
        )
        cls.user_role, _ = Role.objects.get_or_create(name="user")
        cls.vendor_role, _ = Role.objects.get_or_create(name="vendor")
        cls.rider_role, _ = Role.objects.get_or_create(name="rider")
        cls.user.roles.add(cls.user_role)
        cls.user.roles.add(cls.vendor_role)
        cls.user.roles.add(cls.rider_role)

    def test_user_model(self):
        self.assertEqual(self.user.email, "testuser@gmail.com")
        self.assertTrue(self.user.check_password("user1234"))
        self.assertIn(self.vendor_role, self.user.roles.all())
        self.assertIn(self.rider_role, self.user.roles.all())

    def test_default_fields(self):
        self.assertEqual(self.user.is_active, True)
        self.assertEqual(self.user.is_superuser, False)
        self.assertIn(self.user_role, self.user.roles.all())

    def test_user_profile(self):
        self.assertEqual(self.user.user_profile.first_name, "test")
        self.assertEqual(self.user.user_profile.last_name, "user")
        self.assertEqual(self.user.user_profile.phone_number, "08012345678")
        self.assertEqual(self.user.user_profile.gender, "male")

    def test_user_rider_profile(self):
        self.assertIsNotNone(getattr(self.user, "rider_profile", None))
        self.assertEqual(self.user.rider_profile.phone_number2, "08012345678")
        self.assertEqual(self.user.rider_profile.nin, "123456789")
        self.assertEqual(self.user.rider_profile.next_of_kin, "test person")
        self.assertEqual(self.user.rider_profile.motorcycle_type, "bike")
        self.assertEqual(self.user.rider_profile.motorcycle_brand, "Honda")

    def test_user_vendor_profile(self):
        self.assertIsNotNone(getattr(self.user, "vendor_profile", None))
        self.assertEqual(self.user.vendor_profile.business_name, "Test business")
        self.assertEqual(self.user.vendor_profile.business_location_city, "Test city")
        self.assertEqual(self.user.vendor_profile.business_location_state, "Test state")

    def test_vendor_profile_str(self):
        """Test the string rep of the user model"""
        self.assertEqual(
            str(self.vendorProfile),
            f"Vendor: {self.vendorProfile.business_name} [{self.vendorProfile.user.email}]",
        )


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class ProfileAPITest(TestCase):
    """Test cases for the user API views"""

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(
            email="testuser@gmail.com",
            password="user1234",
        )
        cls.vendor = CustomUser.objects.create_user(
            email="testvendor@gmail.com",
            password="vendor1234",
        )
        cls.vendorProfile2 = VendorsProfile.objects.create(
            user=cls.vendor,
            business_name="Vendor business",
            business_location_city="Vendor city",
            business_location_state="Vendor state",
        )
        cls.userProfile = UsersProfile.objects.create(
            user=cls.user,
            first_name="test",
            last_name="user",
            phone_number="08012345678",
            gender="male",
            dob=datetime.date(2020, 7, 12),
        )
        cls.vendorProfile = VendorsProfile.objects.create(
            user=cls.user,
            business_name="Test business",
            business_location_city="Test city",
            business_location_state="Test state",
        )
        cls.riderProfile = RidersProfile.objects.create(
            user=cls.user,
            phone_number2="08012345678",
            nin="123456789",
            next_of_kin="test person",
            motorcycle_type="bike",
            motorcycle_brand="Honda",
        )
        cls.user_role, _ = Role.objects.get_or_create(name="user")
        cls.vendor_role, _ = Role.objects.get_or_create(name="vendor")
        cls.rider_role, _ = Role.objects.get_or_create(name="rider")
        cls.user.roles.add(cls.user_role)
        cls.user.roles.add(cls.vendor_role)
        cls.user.roles.add(cls.rider_role)
        cls.vendor.roles.add(cls.user_role)
        cls.vendor.roles.add(cls.vendor_role)
        cls.userProfile.favorite_vendors.add(
            cls.user
        )  # User can favorite themselves for testing

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_vendor(self):
        url = reverse_lazy("rest_register")
        data = {
            "email": "testuser@test.com",
            "password1": "testpassword123",
            "first_name": "string",
            "last_name": "string",
            "phone_number": "08098765432",
            "gender": "male",
            "dob": "2025-06-09",
            "roles": ["vendor"],
            "business_name": "Test business 2",
            "business_location_city": "Test city",
            "business_location_state": "Test state",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_data = response.data["user"]
        self.assertIsNotNone(response.data["access"])
        self.assertNotEqual(response.data["access"], "")
        self.assertIn("user", user_data["roles"])
        self.assertIn("vendor", user_data["roles"])
        self.assertIsNotNone(user_data["user_profile"])
        self.assertEqual(user_data["user_profile"]["first_name"], "string")
        self.assertEqual(user_data["user_profile"]["last_name"], "string")
        self.assertEqual(user_data["user_profile"]["phone_number"], "08098765432")
        self.assertEqual(user_data["user_profile"]["gender"], "male")
        self.assertEqual(
            user_data["vendor_profile"]["business_name"], "Test business 2"
        )
        self.assertEqual(
            user_data["vendor_profile"]["business_location_city"], "Test city"
        )
        self.assertEqual(
            user_data["vendor_profile"]["business_location_state"], "Test state"
        )
        self.assertIsNone(user_data["rider_profile"])

    def test_create_without_adding_vendor_role(self):
        """Test what happens when the vendor role is not added when creating a vendor"""
        url = reverse_lazy("rest_register")
        data = {
            "email": "testuser@test.com",
            "password1": "testpassword123",
            "first_name": "string",
            "last_name": "string",
            "phone_number": "08011111111",
            "gender": "male",
            "dob": "2025-06-09",
            "business_name": "Test business 2",
            "business_location_city": "Test city",
            "business_location_state": "Test state",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_data = response.data["user"]
        self.assertIsNotNone(response.data["access"])
        self.assertNotEqual(response.data["access"], "")
        self.assertIn("user", user_data["roles"])
        self.assertIsNotNone(user_data["user_profile"])
        self.assertNotIn("vendor", user_data["roles"])
        self.assertIsNone(user_data["vendor_profile"])

    def test_vendor_login(self):
        """Test user login endpoint"""
        url = reverse_lazy("rest_login")
        data = {
            "email": "testuser@gmail.com",
            "password": "user1234",
        }
        response = self.client.post(url, data, format="json")
        user_data = response.data["user"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user_data["email"], "testuser@gmail.com")
        self.assertIsNone(user_data.get("password", None))
        self.assertIsNotNone(user_data.get("user_profile"))
        self.assertEqual(user_data["user_profile"]["first_name"], "test")
        self.assertEqual(user_data["user_profile"]["last_name"], "user")
        self.assertEqual(user_data["user_profile"]["gender"], "male")
        self.assertIn("user", user_data["roles"])
        self.assertIn("vendor", user_data["roles"])
        self.assertIsNotNone(response.data["access"])
        self.assertNotEqual(response.data["access"], "")
        self.assertEqual(user_data["vendor_profile"]["business_name"], "Test business")
        self.assertEqual(
            user_data["vendor_profile"]["business_location_city"], "Test city"
        )
        self.assertEqual(
            user_data["vendor_profile"]["business_location_state"], "Test state"
        )

    def test_get_vendor_profile(self):
        """Test viewing user profile info"""
        url = reverse_lazy("rest_user_details")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_data = response.data
        self.assertIn("user", user_data["roles"])
        self.assertIn("vendor", user_data["roles"])
        self.assertEqual(user_data["email"], "testuser@gmail.com")
        self.assertIsNotNone(user_data["user_profile"])
        self.assertEqual(user_data["user_profile"]["first_name"], "test")
        self.assertEqual(user_data["user_profile"]["last_name"], "user")
        self.assertEqual(user_data["user_profile"]["phone_number"], "08012345678")
        self.assertEqual(user_data["user_profile"]["gender"], "male")
        self.assertIsNotNone(user_data["vendor_profile"])
        self.assertEqual(user_data["vendor_profile"]["business_name"], "Test business")
        self.assertEqual(
            user_data["vendor_profile"]["business_location_city"], "Test city"
        )
        self.assertEqual(
            user_data["vendor_profile"]["business_location_state"], "Test state"
        )
        self.assertIn("vendor", user_data["roles"])

    def test_update_vendor(self):
        """Test updating a user profile"""
        url = reverse_lazy("rest_user_details")
        data = {
            "roles": [],
            "vendor_profile": {
                "business_name": "Second test business",
                "business_location_city": "Igando",
            },
        }
        response = self.client.patch(url, data, format="json")
        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_data = response.data
        self.assertEqual(self.user.vendor_profile.business_name, "Second test business")
        self.assertEqual(self.user.vendor_profile.business_location_city, "Igando")
        # Ensure unedited fields remain the same
        self.assertIsNotNone(user_data["user_profile"])
        self.assertEqual(self.user.email, "testuser@gmail.com")
        self.assertEqual(self.user.user_profile.first_name, "test")
        self.assertEqual(self.user.user_profile.last_name, "user")
        self.assertEqual(self.user.user_profile.phone_number, "08012345678")
        self.assertEqual(self.user.vendor_profile.business_location_state, "Test state")
        self.assertIn("user", user_data["roles"])
        self.assertIn("vendor", user_data["roles"])
        self.assertIn("rider", user_data["roles"])

    def test_update_readonly_fields(self):
        """Update readonly fields like is_active. Should give an error"""
        url = reverse_lazy("rest_user_details")
        data = {
            "is_verified": True,
        }
        response = self.client.patch(url, data, format="json")
        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.vendor_profile.is_verified, False)

    def test_get_all_vendor_profiles(self):
        """Test viewing all vendor profiles"""
        url = reverse_lazy("vendor-profile-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"], list)
        self.assertEqual(len(response.data["data"]), 2)
        vendor_profile = response.data["data"][0]
        self.assertIn(
            vendor_profile["business_name"], ["Test business", "Vendor business"]
        )
        self.assertIn(
            vendor_profile["business_location_city"], ["Test city", "Vendor city"]
        )
        self.assertIn(
            vendor_profile["business_location_state"], ["Test state", "Vendor state"]
        )
        self.assertIn("is_verified", vendor_profile)
        self.assertEqual(vendor_profile["is_verified"], False)

    def test_get_single_vendor_profile(self):
        """Test viewing a single vendor profile"""
        url = reverse_lazy("vendor-profile-detail", args=[self.user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        vendor_profile = response.data["data"]
        self.assertEqual(vendor_profile["business_name"], "Test business")
        self.assertEqual(vendor_profile["business_location_city"], "Test city")
        self.assertEqual(vendor_profile["business_location_state"], "Test state")
        self.assertIn("is_verified", vendor_profile)
        self.assertEqual(vendor_profile["is_verified"], False)

    def test_get_favorite_vendors(self):
        """Test viewing user's favorite vendors"""
        url = reverse_lazy("favourite-vendor-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"], list)
        self.assertGreaterEqual(len(response.data["data"]), 1)
        vendor = response.data["data"][0]
        self.assertEqual(vendor["business_name"], "Test business")
        self.assertEqual(vendor["business_location_city"], "Test city")
        self.assertEqual(vendor["business_location_state"], "Test state")
        self.assertIn("is_verified", vendor)
        self.assertEqual(vendor["is_verified"], False)

    def test_add_favorite_vendor(self):
        """Test adding a vendor to user's favorite vendors"""
        url = reverse_lazy("favourite-vendor-list")
        data = {"vendor_id": str(self.vendor.id)}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)
        self.assertEqual(
            response.data["message"], "Vendor added to favorites successfully"
        )
        self.assertIn(self.vendor, self.user.user_profile.favorite_vendors.all())

    def test_add_already_existing_favorite_vendor(self):
        """Test adding a vendor that is already in user's favorite vendors"""
        url = reverse_lazy("favourite-vendor-list")
        data = {"vendor_id": str(self.user.id)}
        self.user.refresh_from_db()
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)
        self.assertEqual(
            response.data["message"], "Vendor added to favorites successfully"
        )
        self.assertIn(self.user, self.user.user_profile.favorite_vendors.all())
        self.assertEqual(
            self.user.user_profile.favorite_vendors.filter(id=self.user.id).count(), 1
        )

    def test_add_nonexistent_favorite_vendor(self):
        """Test adding a vendor that does not exist to user's favorite vendors"""
        url = reverse_lazy("favourite-vendor-list")
        data = {"vendor_id": "123e4567-e89b-12d3-a456-426614174000"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "Vendor not found")

    def test_remove_favorite_vendor(self):
        """Test removing a vendor from user's favorite vendors"""
        url = reverse_lazy("favourite-vendor-detail", args=[str(self.user.id)])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn("message", response.data)
        self.assertEqual(
            response.data["message"], "Vendor removed from favorites successfully"
        )
        self.assertNotIn(self.user, self.user.user_profile.favorite_vendors.all())

    def test_remove_nonexistent_favorite_vendor(self):
        """Test removing a vendor that does not exist from user's favorite vendors"""
        url = reverse_lazy(
            "favourite-vendor-detail", args=["123e4567-e89b-12d3-a456-426614174000"]
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "Vendor not found")

    def test_remove_existing_vendor_not_in_favorites(self):
        """Test removing a vendor that is not in user's favorite vendors"""
        url = reverse_lazy("favourite-vendor-detail", args=[str(self.vendor.id)])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn("message", response.data)
        self.assertEqual(
            response.data["message"], "Vendor removed from favorites successfully"
        )
        self.assertNotIn(self.vendor, self.user.user_profile.favorite_vendors.all())


class SensitiveActionsForVendorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vendor = CustomUser.objects.create_user(
            email="testvendor@gmail.com",
            password="vendor1234",
        )
        cls.vendorProfile = VendorsProfile.objects.create(
            user=cls.vendor,
            business_name="Vendor business",
            business_location_city="Vendor city",
            business_location_state="Vendor state",
            bank_code="001",
            account_number="12345",
        )
        cls.vendor_role, _ = Role.objects.get_or_create(name="vendor")
        cls.vendor.roles.add(cls.vendor_role)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.vendor)

        self.bank_url = reverse_lazy("update-bank-details")
        # self.email_url = reverse_lazy("update-email")
        # self.password_url = reverse_lazy("change-password")

    def test_update_bank_details_with_correct_password(self):
        """Test bank details are updated and verified
        with correct password before commiting changes
        """
        data = {
            "password": "vendor1234",
            "account_number": "123456",
            "bank_code": "002",
        }
        resp = self.client.patch(self.bank_url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.vendorProfile.refresh_from_db()

        self.assertEqual(self.vendorProfile.bank_code, "002")
        self.assertEqual(self.vendorProfile.account_number, "123456")
        # self.assertEqual(resp.data["bank_name"], "Test Bank")

    def test_update_bank_details_with_wrong_password(self):
        """Test bank details are updated and verified
        with wrong password throws an error
        """
        data = {
            "password": "vendor123",
            "account_number": "123456",
            "bank_code": "002",
        }
        response = self.client.patch(self.bank_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.vendorProfile.bank_code, "001")
        self.assertEqual(self.vendorProfile.account_number, "12345")
        self.assertIn("password", response.data)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
class PhoneVerificationTests(TestCase):
    """Tests for phone number verification system"""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email="testuser@example.com",
            password="testpass123",
        )
        self.user_profile = UsersProfile.objects.create(
            user=self.user,
            first_name="Test",
            last_name="User",
            phone_number="08012345678",
        )

    def test_check_phone_available(self):
        """Test checking if a phone number is available"""
        response = self.client.get(
            reverse_lazy("check-phone"),
            {"phone_number": "08098765432"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["data"]["exists"])
        self.assertEqual(response.data["data"]["phone_number"], "08098765432")

    def test_check_phone_already_exists(self):
        """Test checking if a phone number already exists"""
        response = self.client.get(
            reverse_lazy("check-phone"),
            {"phone_number": "08012345678"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"]["exists"])

    def test_check_phone_missing_parameter(self):
        """Test checking phone without phone_number parameter"""
        response = self.client.get(reverse_lazy("check-phone"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data["message"])

    def test_verify_phone_authenticated(self):
        """Test verifying phone number when authenticated"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse_lazy("verify-phone"))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"]["is_phone_verified"])
        self.assertIsNotNone(response.data["data"]["phone_verified_at"])

    def test_verify_phone_not_authenticated(self):
        """Test verifying phone number without authentication"""
        response = self.client.post(reverse_lazy("verify-phone"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_verify_phone_updates_timestamp(self):
        """Test that phone_verified_at timestamp is set"""
        self.client.force_authenticate(user=self.user)
        before_verify = timezone.now()
        response = self.client.post(reverse_lazy("verify-phone"))
        after_verify = timezone.now()
        
        self.user_profile.refresh_from_db()
        self.assertTrue(self.user_profile.is_phone_verified)
        self.assertIsNotNone(self.user_profile.phone_verified_at)
        self.assertGreaterEqual(self.user_profile.phone_verified_at, before_verify)
        self.assertLessEqual(self.user_profile.phone_verified_at, after_verify)

    def test_duplicate_phone_on_registration(self):
        """Test that registration fails with duplicate phone number"""
        from apps.userAuth.serializers import CustomRegisterSerializer
        
        data = {
            "email": "another@example.com",
            "password1": "testpass123",
            "password2": "testpass123",
            "first_name": "Another",
            "last_name": "User",
            "phone_number": "08012345678",  # Already used
        }
        
        serializer = CustomRegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("phone_number", serializer.errors)

    def test_phone_number_unique_constraint(self):
        """Test database unique constraint on phone_number"""
        from django.db import IntegrityError
        
        with self.assertRaises(IntegrityError):
            UsersProfile.objects.create(
                user=CustomUser.objects.create_user(
                    email="another@example.com",
                    password="testpass123",
                ),
                first_name="Another",
                last_name="User",
                phone_number="08012345678",  # Duplicate
            )

    def test_new_user_phone_not_verified_by_default(self):
        """Test that newly registered users have is_phone_verified=False"""
        new_user = CustomUser.objects.create_user(
            email="newuser@example.com",
            password="testpass123",
        )
        new_profile = UsersProfile.objects.create(
            user=new_user,
            first_name="New",
            last_name="User",
            phone_number="08011111111",
        )
        
        self.assertFalse(new_profile.is_phone_verified)
        self.assertIsNone(new_profile.phone_verified_at)

    def test_verify_phone_multiple_times(self):
        """Test that phone can be verified multiple times"""
        self.client.force_authenticate(user=self.user)
        
        # First verification
        response1 = self.client.post(reverse_lazy("verify-phone"))
        self.assertTrue(response1.data["data"]["is_phone_verified"])
        timestamp1 = response1.data["data"]["phone_verified_at"]
        
        # Second verification
        response2 = self.client.post(reverse_lazy("verify-phone"))
        self.assertTrue(response2.data["data"]["is_phone_verified"])
        timestamp2 = response2.data["data"]["phone_verified_at"]
        
        # Timestamps should be different (second one later)
        self.assertNotEqual(timestamp1, timestamp2)
