from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from .models import CustomUser

class UserTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            first_name = 'test',
            last_name = 'user',
            username='testuser',
            email = 'testuser@gmail.com',
            password='user1234',
            phone_number='08012345678',
            role='buyer'
        )

        cls.client = Client()
    
    def test_user_model(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'testuser@gmail.com')
        self.assertEqual(self.user.first_name, 'test')
        self.assertEqual(self.user.last_name, 'user')
        self.assertTrue(self.user.check_password('user1234'))
    
    def test_default_fields(self):
        self.assertEqual(self.user.status, 'active')
        self.assertEqual(self.user.role, 'buyer')

    def test_user_login(self):
        login_success = self.client.login(email='testuser@gmail.com', password='user1234')
        login_failed = self.client.login(email='testuser@gmail.com', password='testuser')
        self.assertTrue(login_success)
        self.assertFalse(login_failed)
    
    def test_user_instance(self):
        self.assertTrue(isinstance(self.user, CustomUser))

