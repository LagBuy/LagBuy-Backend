from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from apps.userAuth.models import CustomUser, Role
from apps.profiles.models import UsersProfile
from apps.orders.models import Order, OrderItem
from apps.products.models import Product, Category
from apps.payments.models import Payment, PaymentStatus


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class VendorDashboardTest(TestCase):
    """Test the total sale view"""

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(
            email="test@user.com",
            password="testpassword"
        )
        cls.userProfile = UsersProfile.objects.create(
            user=cls.user,
            first_name="Buyer",
            last_name="Test",
            phone_number="0909222002",
        )
        cls.seller = CustomUser.objects.create_user(
            email="test@seller.com",
            password="testpassword"
        )
        cls.seller2 = CustomUser.objects.create_user(
            email="test2@seller.com",
            password="testpassword"
        )
        cls.user_role = Role.objects.create(name='user')
        cls.vendor_role = Role.objects.create(name='vendor')
        cls.user.roles.add(cls.user_role)
        cls.seller.roles.add(cls.user_role)
        cls.seller.roles.add(cls.vendor_role)
        cls.seller2.roles.add(cls.user_role)
        cls.seller2.roles.add(cls.vendor_role)

        cls.product = Product.objects.create(
            name="Test Product",
            price=100.0,
            description="Test Description",
            stock_quantity=10,
            seller=cls.seller,
        )
        cls.product2 = Product.objects.create(
            name="Another Product",
            price=50.0,
            description="Another Description",
            stock_quantity=4,
            seller=cls.seller,
        )
        cls.product3 = Product.objects.create(
            name="Another Product 3",
            price=500.0,
            description="Another Description",
            stock_quantity=3,
            seller=cls.seller2,
        )
        cls.category1 = Category.objects.create(name="First Category")
        cls.category2 = Category.objects.create(name="Second Category")
        cls.product.categories.add(cls.category1)
        # cls.product.categories.add(cls.category2)
        cls.product2.categories.add(cls.category2)
        cls.product3.categories.add(cls.category2)

        cls.order = Order.objects.create(
            buyer=cls.user, delivery_address="123 Test St"
        )
        cls.order_item = OrderItem.objects.create(
            order=cls.order, product=cls.product, quantity=2
        )
        cls.order_item2 = OrderItem.objects.create(
            order=cls.order, product=cls.product3, quantity=2
        )
        cls.order2 = Order.objects.create(
            buyer=cls.user, delivery_address="123 Test St"
        )
        cls.order_item3 = OrderItem.objects.create(
            order=cls.order2, product=cls.product2, quantity=2
        )

        cls.payment1 = Payment.objects.create(
            user=cls.user,
            order=cls.order,
            amount=cls.order.total_price,
            currency="NGN",
            ref="test_ref_vendors_analytics",
            payment_status=PaymentStatus.PAID,
        )
        cls.payment2 = Payment.objects.create(
            user=cls.user,
            order=cls.order2,
            amount=cls.order2.total_price,
            currency="NGN",
            ref="test_ref_vendors_analytics2",
            payment_status=PaymentStatus.PAID,
        )

        # unpaid order
        cls.unpaid_order = Order.objects.create(
            buyer=cls.user, delivery_address="123 Test St"
        )
        cls.order_item4 = OrderItem.objects.create(
            order=cls.unpaid_order, product=cls.product, quantity=2
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.seller)
    
    def test_vendor_product_list(self):
        """Test the vendor product list view"""
        url = reverse_lazy("vendor-products")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(len(data), 2)
        product_names = [product["name"] for product in data]
        self.assertIn("Test Product", product_names)
        self.assertIn("Another Product", product_names)
    
    def test_total_sale(self):
        """Test vendor total sale view. Ensures the unpaid order is not added
           Ensure it only includes products owned by the logged in user
        """
        url = reverse_lazy("total-sale")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["total_sale"], 300.0)

    def test_non_seller_cannot_access(self):
        """Test to ensure only vendors can access this view"""
        self.client.force_authenticate(user=self.user)
        url = reverse_lazy("total-sale")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_vendor_total_product(self):
        """Test the total product a vendor has"""
        url = reverse_lazy("total-product")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["total_product"], 2)
    
    def test_new_customers(self):
        """Test the number of new unique customers a vendor had in the past 30 days"""
        url = reverse_lazy("new-customers")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["new_customers_count"], 1)
        self.assertEqual(data['new_customers'][0]['first_name'], 'Buyer')
    
    def test_new_customers_in_90_days(self):
        """Test the number of new unique customers a vendor had in the past 30 days"""
        url = reverse_lazy("new-customers")
        response = self.client.get(url, days=90)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["new_customers_count"], 1)
        self.assertEqual(data['new_customers'][0]['first_name'], 'Buyer')
    
    def test_sale_per_month(self):
        """Test the total sale per month view.
        Returns the total sale for each month for one year.
        """
        url = reverse_lazy("total-sale-per-month")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(len(data), 13)

        current_month = timezone.now()
        prev_month = timezone.now() - relativedelta(years=1)
        key = current_month.strftime("%m-%Y")
        key2 = prev_month.strftime("%m-%Y")

        self.assertEqual(data[key], 300.0)
        self.assertEqual(data[key2], 0)
    
    def test_low_stock_count(self):
        """Test low stock count view"""
        url = reverse_lazy("low-stock-count")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["low_stock_count"], 1)
        self.assertEqual(data["low_stock_products"][0]["name"], "Another Product")
    
    def test_low_stock_count_less_than_20(self):
        """Test low stock count view"""
        url = reverse_lazy("low-stock-count")
        response = self.client.get(url, { "lt": 20 })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["low_stock_count"], 2)
        self.assertEqual(data["low_stock_products"][0]["name"], "Another Product")
    
    def test_low_stock_count_with_negative_value(self):
        """Test low stock count view"""
        url = reverse_lazy("low-stock-count")
        response = self.client.get(url, { "lt": -5 })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["low_stock_count"], 0)

    def test_category_distribution(self):
        """Test category distribution endpoint"""
        url = reverse_lazy("category-distribution")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["First Category"], 50.0)
        self.assertEqual(data["Second Category"], 50.0)

