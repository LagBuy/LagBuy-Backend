import uuid
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from apps.notifications.models import WebhookEvent, Notification


User = get_user_model()


class WebhookReceiverViewTests(APITestCase):
    """Tests for the webhook receiver endpoint"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("notifications-webhook")
        self.user = User.objects.create_user(
            email="test@example.com", password="pass123"
        )

    def test_webhook_creates_event(self):
        """Webhook should log new event in DB"""
        payload = {
            "event_id": str(uuid.uuid4()),
            "status": "success",
            "customer_email": self.user.email,
            "amount": 5000,
        }

        response = self.client.post(
            self.url, payload, format="json", HTTP_X_WEBHOOK_SOURCE="paystack"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(WebhookEvent.objects.filter(event_id=payload["event_id"]).exists())

    def test_duplicate_event_ignored(self):
        """Same event_id should not create duplicates"""
        event_id = str(uuid.uuid4())

        WebhookEvent.objects.create(
            event_id=event_id,
            source="paystack",
            payload={"test": "data"},
            processed=True,
        )

        payload = {"event_id": event_id, "status": "success"}
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(WebhookEvent.objects.filter(event_id=event_id).count(), 1)

    def test_webhook_creates_notification_on_success(self):
        """Webhook with success status should notify user"""
        payload = {
            "event_id": str(uuid.uuid4()),
            "status": "success",
            "customer_email": self.user.email,
            "amount": 10000,
        }

        response = self.client.post(self.url, payload, format="json")
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data}")
        print(f"Notifications count: {Notification.objects.count()}")
        print(f"User email: {self.user.email}")
        self.assertTrue(Notification.objects.filter(user=self.user).exists())

    def test_failed_webhook_increments_retry(self):
        """Webhook should increment retry count on processing error"""
        # Send bad payload that causes exception (missing status)
        payload = {"event_id": str(uuid.uuid4())}
        response = self.client.post(self.url, payload, format="json")

        event = WebhookEvent.objects.get(event_id=payload["event_id"])
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertGreater(event.retries, 0)
