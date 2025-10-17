from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from apps.notifications.models import Notification

User = get_user_model()


class TestNotificationsAPI(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com", password="pass123"
        )
        self.client.force_authenticate(user=self.user)

    def test_list_notifications(self):
        Notification.objects.create(user=self.user, message="First notification")
        Notification.objects.create(user=self.user, message="Second notification")

        url = reverse("notifications-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["message"], "Second notification")

    def test_mark_notification_as_read(self):
        notification = Notification.objects.create(user=self.user, message="Mark me read")

        url = reverse("notification-mark-read", args=[notification.id])
        response = self.client.patch(url)

        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
