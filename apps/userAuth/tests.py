from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
import datetime

from apps.profiles.models import UsersProfile, VendorsProfile, RidersProfile
from .models import CustomUser, Role


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class UserTests(TestCase):
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
        cls.user_role, _ = Role.objects.get_or_create(name='user')
        cls.user.roles.add(cls.user_role)

    def test_user_model(self):
        self.assertEqual(self.user.email, 'testuser@gmail.com')
        self.assertTrue(self.user.check_password('user1234'))
        self.assertIsNone(getattr(self.user, 'vendor_profile', None))
    
    def test_default_fields(self):
        self.assertEqual(self.user.is_active, True)
        self.assertEqual(self.user.is_superuser, False)
        self.assertIn(self.user_role, self.user.roles.all())
    
    def test_user_str(self):
        """Test the string rep of the user model"""
        self.assertEqual(
            str(self.user), f'User: [{self.user.email}]'
        )

    def test_user_instance(self):
        self.assertTrue(isinstance(self.user, CustomUser))


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class UserAPITest(TestCase):
    """Test cases for the user API views"""

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.user = get_user_model().objects.create_user(
            email = 'testuser@gmail.com',
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
        cls.user_role, _ = Role.objects.get_or_create(name='user')
        cls.user.roles.add(cls.user_role)
    
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_create_user(self):
        url = reverse_lazy('rest_register')
        data = {
            "email": "testuser@test.com",
            "password1": "testpassword123",
            "first_name": "string",
            "last_name": "string",
            "phone_number": "08012345678",
            "gender": "male",
            "dob": "2025-06-09",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_data = response.data["user"]
        self.assertIsNotNone(response.data["access"])
        self.assertNotEqual(response.data["access"], "")
        self.assertIn('user', user_data['roles'])
        self.assertIsNotNone(user_data['user_profile'])
        self.assertEqual(user_data['user_profile']['first_name'], 'string')
        self.assertEqual(user_data['user_profile']['last_name'], 'string')
        self.assertEqual(user_data['user_profile']['phone_number'], '08012345678')
        self.assertEqual(user_data['user_profile']['gender'], 'male')
        self.assertIsNone(user_data['vendor_profile'])
        self.assertIsNone(user_data['rider_profile'])

    def test_create_with_missing_required_fields(self):
        """Test what happens when data is incomplete"""
        url = reverse_lazy('rest_register')
        data = {
            "email": "testuser@test.com",
            "password1": "testpassword123",
            "first_name": "string",
            "last_name": "string",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(response.data['phone_number'][0]), 'This field is required.')

    def test_user_login(self):
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
        self.assertIsNotNone(response.data["access"])
        self.assertNotEqual(response.data["access"], "")

    def test_get_user_profile(self):
        """Test viewing user profile info"""
        url = reverse_lazy('rest_user_details')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_data = response.data
        self.assertIn('user', user_data['roles'])
        self.assertEqual(user_data['email'], 'testuser@gmail.com')
        self.assertIsNotNone(user_data['user_profile'])
        self.assertEqual(user_data['user_profile']['first_name'], 'test')
        self.assertEqual(user_data['user_profile']['last_name'], 'user')
        self.assertEqual(user_data['user_profile']['phone_number'], '08012345678')
        self.assertEqual(user_data['user_profile']['gender'], 'male')
        self.assertIsNone(user_data['vendor_profile'])
        self.assertIsNone(user_data['rider_profile'])

    def test_update_user(self):
        """Test updating a user profile"""
        url = reverse_lazy('rest_user_details')
        data = {
            'user_profile': {
                'gender': 'female',
                'address': '3, good man street',
                'city': 'Igando',
            }
        }
        response = self.client.patch(url, data, format='json')
        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_data = response.data
        self.assertEqual(self.user.email, 'testuser@gmail.com')
        self.assertIsNotNone(user_data['user_profile'])
        self.assertEqual(self.user.user_profile.gender, 'female')
        self.assertEqual(self.user.user_profile.address, '3, good man street')
        self.assertEqual(self.user.user_profile.city, 'Igando')
        # Ensure unedited fields remain the same
        self.assertEqual(self.user.user_profile.first_name, 'test')
        self.assertEqual(self.user.user_profile.last_name, 'user')
        self.assertEqual(self.user.user_profile.phone_number, '08012345678')
        self.assertIsNone(getattr(self.user, 'vendor_profile', None))
        self.assertIsNone(getattr(self.user, 'rider_profile', None))

    def test_update_email(self):
        """Try updating the user email. should give an error"""
        url = reverse_lazy('rest_user_details')
        data = {
            'is_active': False,
        }
        response = self.client.patch(url, data, format='json')
        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.email, 'testuser@gmail.com')

    def test_update_readonly_fields(self):
        """Update readonly fields like is_active. Should give an error"""
        url = reverse_lazy('rest_user_details')
        data = {
            'is_active': False,
        }
        response = self.client.patch(url, data, format='json')
        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.is_active, True)
    
    def test_user_change_password(self):
        """Test the user change password endpoint"""
        url = reverse_lazy('rest_password_change')
        data = {
            'new_password1': 'testpassword2',
            'new_password2': 'testpassword2',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'New password has been saved.')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('testpassword2'))
        """login with new password"""
        url = reverse_lazy('rest_login')
        data = {
            "email": "testuser@gmail.com",
            "password": "testpassword2",
        }
        response = self.client.post(url, data, format="json")
        user_data = response.data["user"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user_data['email'], "testuser@gmail.com")


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class ProfileImageTests(TestCase):
    """Test cases for profile image URL field and upload functionality"""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email='imagetest@gmail.com',
            password='user1234',
        )
        cls.userProfile = UsersProfile.objects.create(
            user=cls.user,
            first_name='image',
            last_name='tester',
            phone_number='08012345678',
        )
        cls.user_role, _ = Role.objects.get_or_create(name='user')
        cls.user.roles.add(cls.user_role)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_user_with_image_url(self):
        """Test creating a user with an image URL"""
        url = reverse_lazy('rest_register')
        data = {
            "email": "newuser@test.com",
            "password1": "testpassword123",
            "first_name": "John",
            "last_name": "Doe",
            "phone_number": "08098765432",
            "image": "https://example.com/profile.jpg",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_data = response.data["user"]
        self.assertEqual(user_data['user_profile']['image'], 'https://example.com/profile.jpg')

    def test_update_profile_with_image_url(self):
        """Test updating user profile with an image URL"""
        url = reverse_lazy('rest_user_details')
        data = {
            'user_profile': {
                'image': 'https://cdn.example.com/users/profile-pic.png',
            }
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.user_profile.refresh_from_db()
        self.assertEqual(self.user.user_profile.image, 'https://cdn.example.com/users/profile-pic.png')

    @patch('common.services.storage.STORAGE.upload_file')
    def test_upload_profile_image(self, mock_upload):
        """Test image upload endpoint returns URL"""
        mock_upload.return_value = 'https://storage.example.com/uploads/test-image.jpg'
        
        url = reverse_lazy('upload_profile_image')
        image = SimpleUploadedFile(
            "test_image.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        response = self.client.post(url, {'image': image}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('url', response.data)
        self.assertEqual(response.data['url'], 'https://storage.example.com/uploads/test-image.jpg')
        mock_upload.assert_called_once()

    @patch('common.services.storage.STORAGE.upload_file')
    def test_upload_profile_image_no_file(self, mock_upload):
        """Test image upload endpoint with no file provided"""
        url = reverse_lazy('upload_profile_image')
        response = self.client.post(url, {}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'No image file provided.')
        mock_upload.assert_not_called()

    @patch('common.services.storage.STORAGE.upload_file')
    def test_upload_profile_image_failure(self, mock_upload):
        """Test image upload endpoint when storage fails"""
        mock_upload.return_value = None
        
        url = reverse_lazy('upload_profile_image')
        image = SimpleUploadedFile(
            "test_image.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        response = self.client.post(url, {'image': image}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'Failed to upload image.')



