from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from django.utils import timezone
import datetime

from apps.userAuth.models import CustomUser, Role
from .models import VendorsProfile, UsersProfile, RidersProfile


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class ProfileModelsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email='testuser@gmail.com',
            password='user1234',
        )
        cls.userProfile = UsersProfile.objects.create(
            user=cls.user,
            first_name = 'test',
            last_name = 'user',
            phone_number='08012345678',
            gender='male',
            dob=datetime.date(2020, 7, 12),
        )
        cls.vendorProfile = VendorsProfile.objects.create(
            user=cls.user,
            business_name='Test business',
            business_location_city='Test city',
            business_location_state='Test state',
        )
        cls.riderProfile = RidersProfile.objects.create(
            user=cls.user,
            phone_number2='08012345678',
            nin='123456789',
            next_of_kin='test person',
            motorcycle_type='bike',
            motorcycle_brand='Honda',
        )
        cls.user_role = Role.objects.create(name='user')
        cls.vendor_role = Role.objects.create(name='vendor')
        cls.rider_role = Role.objects.create(name='rider')
        cls.user.roles.add(cls.user_role)
        cls.user.roles.add(cls.vendor_role)
        cls.user.roles.add(cls.rider_role)

    def test_user_model(self):
        self.assertEqual(self.user.email, 'testuser@gmail.com')
        self.assertTrue(self.user.check_password('user1234'))
        self.assertIn(self.vendor_role, self.user.roles.all())
        self.assertIn(self.rider_role, self.user.roles.all())
    
    def test_default_fields(self):
        self.assertEqual(self.user.is_active, True)
        self.assertEqual(self.user.is_superuser, False)
        self.assertIn(self.user_role, self.user.roles.all())
    
    def test_user_profile(self):
        self.assertEqual(self.user.user_profile.first_name, 'test')
        self.assertEqual(self.user.user_profile.last_name, 'user')
        self.assertEqual(self.user.user_profile.phone_number, '08012345678')
        self.assertEqual(self.user.user_profile.gender, 'male')
    
    def test_user_rider_profile(self):
        self.assertIsNotNone(getattr(self.user, 'rider_profile', None))
        self.assertEqual(self.user.rider_profile.phone_number2, '08012345678')
        self.assertEqual(self.user.rider_profile.nin, '123456789')
        self.assertEqual(self.user.rider_profile.next_of_kin, 'test person')
        self.assertEqual(self.user.rider_profile.motorcycle_type, 'bike')
        self.assertEqual(self.user.rider_profile.motorcycle_brand, 'Honda')
    
    def test_user_vendor_profile(self):
        self.assertIsNotNone(getattr(self.user, 'vendor_profile', None))
        self.assertEqual(self.user.vendor_profile.business_name, 'Test business')
        self.assertEqual(self.user.vendor_profile.business_location_city, "Test city")
        self.assertEqual(self.user.vendor_profile.business_location_state, "Test state")
    
    def test_vendor_profile_str(self):
        """Test the string rep of the user model"""
        self.assertEqual(
            str(self.vendorProfile), f'Vendor: {self.vendorProfile.business_name} [{self.vendorProfile.user.email}]'
        )


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class ProfileAPITest(TestCase):
    """Test cases for the user API views"""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email='testuser@gmail.com',
            password='user1234',
        )
        cls.userProfile = UsersProfile.objects.create(
            user=cls.user,
            first_name = 'test',
            last_name = 'user',
            phone_number='08012345678',
            gender='male',
            dob=datetime.date(2020, 7, 12),
        )
        cls.vendorProfile = VendorsProfile.objects.create(
            user=cls.user,
            business_name='Test business',
            business_location_city='Test city',
            business_location_state='Test state',
        )
        cls.riderProfile = RidersProfile.objects.create(
            user=cls.user,
            phone_number2='08012345678',
            nin='123456789',
            next_of_kin='test person',
            motorcycle_type='bike',
            motorcycle_brand='Honda',
        )
        cls.user_role = Role.objects.create(name='user')
        cls.vendor_role = Role.objects.create(name='vendor')
        cls.rider_role = Role.objects.create(name='rider')
        cls.user.roles.add(cls.user_role)
        cls.user.roles.add(cls.vendor_role)
        cls.user.roles.add(cls.rider_role)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_vendor(self):
        url = reverse_lazy('rest_register')
        data = {
            "email": "testuser@test.com",
            "password1": "testpassword123",
            "first_name": "string",
            "last_name": "string",
            "phone_number": "08012345678",
            "gender": "male",
            "dob": "2025-06-09",
            "roles": ["vendor"],
            "business_name": "Test business 2",
            "business_location_city": "Test city",
            "business_location_state": "Test state"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_data = response.data["user"]
        self.assertIsNotNone(response.data["access"])
        self.assertNotEqual(response.data["access"], "")
        self.assertIn('user', user_data['roles'])
        self.assertIn('vendor', user_data['roles'])
        self.assertIsNotNone(user_data['user_profile'])
        self.assertEqual(user_data['user_profile']['first_name'], 'string')
        self.assertEqual(user_data['user_profile']['last_name'], 'string')
        self.assertEqual(user_data['user_profile']['phone_number'], '08012345678')
        self.assertEqual(user_data['user_profile']['gender'], 'male')
        self.assertEqual(user_data['vendor_profile']['business_name'], 'Test business 2')
        self.assertEqual(user_data['vendor_profile']['business_location_city'], 'Test city')
        self.assertEqual(user_data['vendor_profile']['business_location_state'], 'Test state')
        self.assertIsNone(user_data['rider_profile'])

    def test_create_without_adding_vendor_role(self):
        """Test what happens when the vendor role is not added when creating a vendor"""
        url = reverse_lazy('rest_register')
        data = {
            "email": "testuser@test.com",
            "password1": "testpassword123",
            "first_name": "string",
            "last_name": "string",
            "phone_number": "08012345678",
            "gender": "male",
            "dob": "2025-06-09",
            "business_name": "Test business 2",
            "business_location_city": "Test city",
            "business_location_state": "Test state"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_data = response.data["user"]
        self.assertIsNotNone(response.data["access"])
        self.assertNotEqual(response.data["access"], "")
        self.assertIn('user', user_data['roles'])
        self.assertIsNotNone(user_data['user_profile'])
        self.assertNotIn('vendor', user_data['roles'])
        self.assertIsNone(user_data['vendor_profile'])


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
        self.assertEqual(user_data['email'], "testuser@gmail.com")
        self.assertIsNone(user_data.get('password', None))
        self.assertIsNotNone(user_data.get('user_profile'))
        self.assertEqual(user_data['user_profile']['first_name'], "test")
        self.assertEqual(user_data['user_profile']['last_name'], "user")
        self.assertEqual(user_data['user_profile']['gender'], "male")
        self.assertIn('user', user_data['roles'])
        self.assertIn('vendor', user_data['roles'])
        self.assertIsNotNone(response.data["access"])
        self.assertNotEqual(response.data["access"], "")
        self.assertEqual(user_data['vendor_profile']['business_name'], 'Test business')
        self.assertEqual(user_data['vendor_profile']['business_location_city'], 'Test city')
        self.assertEqual(user_data['vendor_profile']['business_location_state'], 'Test state')

    def test_get_vendor_profile(self):
        """Test viewing user profile info"""
        url = reverse_lazy('rest_user_details')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_data = response.data
        self.assertIn('user', user_data['roles'])
        self.assertIn('vendor', user_data['roles'])
        self.assertEqual(user_data['email'], 'testuser@gmail.com')
        self.assertIsNotNone(user_data['user_profile'])
        self.assertEqual(user_data['user_profile']['first_name'], 'test')
        self.assertEqual(user_data['user_profile']['last_name'], 'user')
        self.assertEqual(user_data['user_profile']['phone_number'], '08012345678')
        self.assertEqual(user_data['user_profile']['gender'], 'male')
        self.assertIsNotNone(user_data['vendor_profile'])
        self.assertEqual(user_data['vendor_profile']['business_name'], 'Test business')
        self.assertEqual(user_data['vendor_profile']['business_location_city'], 'Test city')
        self.assertEqual(user_data['vendor_profile']['business_location_state'], 'Test state')
        self.assertIn('vendor', user_data['roles'])

    def test_update_vendor(self):
        """Test updating a user profile"""
        url = reverse_lazy('rest_user_details')
        data = {
            'roles': [],
            'vendor_profile': {
                'business_name': 'Second test business',
                'business_location_city': 'Igando',
            }
        }
        response = self.client.patch(url, data, format='json')
        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_data = response.data
        self.assertEqual(self.user.vendor_profile.business_name, 'Second test business')
        self.assertEqual(self.user.vendor_profile.business_location_city, 'Igando')
        # Ensure unedited fields remain the same
        self.assertIsNotNone(user_data['user_profile'])
        self.assertEqual(self.user.email, 'testuser@gmail.com')
        self.assertEqual(self.user.user_profile.first_name, 'test')
        self.assertEqual(self.user.user_profile.last_name, 'user')
        self.assertEqual(self.user.user_profile.phone_number, '08012345678')
        self.assertEqual(self.user.vendor_profile.business_location_state, 'Test state')
        self.assertIn('user', user_data['roles'])
        self.assertIn('vendor', user_data['roles'])
        self.assertIn('rider', user_data['roles'])

    def test_update_readonly_fields(self):
        """Update readonly fields like is_active. Should give an error"""
        url = reverse_lazy('rest_user_details')
        data = {
            'is_verified': True,
        }
        response = self.client.patch(url, data, format='json')
        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.vendor_profile.is_verified, False)
    

