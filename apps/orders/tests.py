from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Order

User = get_user_model()


class OrderTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.admin_user = User.objects.create_superuser(
            username="adminuser", password="adminpass"
        )
        self.client.login(username="testuser", password="testpass")
        self.order = Order.objects.create(
            buyer=self.user,
            total_price=100.00,
            delivery_fee=10.00,
            delivery_address="123 Test St",
        )
        self.order_url = reverse("order_detail", kwargs={"pk": self.order.pk})
        self.order_list_url = reverse("order_list")

    def test_list_orders(self):
        response = self.client.get(self.order_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_list_orders(self):
        self.client.logout()
        self.client.login(username="adminuser", password="adminpass")
        response = self.client.get(self.order_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_list_orders(self):
        self.client.logout()
        response = self.client.get(self.order_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_order(self):
        data = {
            "buyer": self.user.id,
            "total_price": 150.00,
            "delivery_fee": 15.00,
            "delivery_address": "456 Test Ave",
        }
        response = self.client.post(self.order_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_order(self):
        response = self.client.get(self.order_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.order.id)

    def test_update_order(self):
        data = {
            "total_price": 200.00,
            "delivery_fee": 20.00,
            "delivery_address": "789 Test Blvd",
        }
        response = self.client.put(self.order_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_price, 200.00)

    def test_partial_update_order(self):
        data = {
            "total_price": 250.00,
        }
        response = self.client.patch(self.order_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_price, 250.00)

    def test_delete_order(self):
        response = self.client.delete(self.order_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(pk=self.order.pk).exists())
