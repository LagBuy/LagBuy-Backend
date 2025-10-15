from decimal import Decimal
import tempfile
from dateutil.relativedelta import relativedelta
from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.notifications.models import Notification
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment, PaymentStatus
from apps.products.models import Category, Product
from apps.profiles.models import UsersProfile, VendorsProfile
from apps.userAuth.models import CustomUser, Role
from apps.vendors.models import AuditLog, ExportJob, VendorWallet
from django.utils.crypto import get_random_string
from django.core.management import call_command

# create a temp dir at import-time so override_settings can use it
TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix="test_media_")


@override_settings(PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",))
class VendorDashboardTest(TestCase):
    """Test the total sale view"""

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(
            email="test@user.com", password="testpassword"
        )
        cls.userProfile = UsersProfile.objects.create(
            user=cls.user,
            first_name="Buyer",
            last_name="Test",
            phone_number="0909222002",
        )
        cls.seller = CustomUser.objects.create_user(
            email="test@seller.com", password="testpassword"
        )
        cls.seller2 = CustomUser.objects.create_user(
            email="test2@seller.com", password="testpassword"
        )
        cls.user_role = Role.objects.create(name="user")
        cls.vendor_role = Role.objects.create(name="vendor")
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

        cls.order = Order.objects.create(buyer=cls.user, delivery_address="123 Test St")
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
        self.assertEqual(data["new_customers"][0]["first_name"], "Buyer")

    def test_new_customers_in_90_days(self):
        """Test the number of new unique customers a vendor had in the past 30 days"""
        url = reverse_lazy("new-customers")
        response = self.client.get(url, days=90)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["new_customers_count"], 1)
        self.assertEqual(data["new_customers"][0]["first_name"], "Buyer")

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
        response = self.client.get(url, {"lt": 20})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["low_stock_count"], 2)
        self.assertEqual(data["low_stock_products"][0]["name"], "Another Product")

    def test_low_stock_count_with_negative_value(self):
        """Test low stock count view"""
        url = reverse_lazy("low-stock-count")
        response = self.client.get(url, {"lt": -5})
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

    def test_vendor_analytics_merged_endpoint(self):
        """Test the combined vendor analytics endpoint returns expected values."""
        url = reverse_lazy("vendor-analytics")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["data"]
        print(data, "respsonse data from vendor_analytics")

        # core numbers that must match existing separate endpoints
        self.assertIn("total_sales", data)
        self.assertEqual(data["total_sales"], 300.0)  # same as test_total_sale

        self.assertIn("total_products", data)
        self.assertEqual(data["total_products"], 2)  # same as test_vendor_total_product

        self.assertIn("new_customers_count", data)
        self.assertEqual(data["new_customers_count"], 1)  # same as test_new_customers

        # sales_per_month should be 13 entries and current month key contains 300.0
        self.assertIn("sales_per_month", data)
        self.assertEqual(len(data["sales_per_month"]), 13)
        current_month_key = timezone.now().strftime("%m-%Y")
        self.assertEqual(data["sales_per_month"][current_month_key], 300.0)

        # low stock & category distribution
        self.assertIn("low_stock_count", data)
        self.assertEqual(data["low_stock_count"], 1)

        self.assertIn("category_distribution", data)
        self.assertEqual(data["category_distribution"]["First Category"], 50.0)
        self.assertEqual(data["category_distribution"]["Second Category"], 50.0)

    def test_vendor_sales_report(self):
        """Test the vendor sales report endpoint returns correct totals and lists"""
        url = reverse_lazy("vendor-sales-report")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data.get("data")
        self.assertIsNotNone(payload)
        totals = payload.get("totals")
        # orders containing this seller's products: order and order2
        self.assertEqual(totals.get("orders"), 2)
        self.assertEqual(int(totals.get("quantity_sold")), 4)
        self.assertEqual(float(totals.get("revenue")), 300.0)

        # top_5 and bottom_5 should be present
        self.assertIn("top_5", payload)
        self.assertIn("bottom_5", payload)
        self.assertTrue(len(payload.get("top_5", [])) >= 1)

    def test_lost_customers_export_uploads_csv(self):
        """Ensure lost customers export builds CSV and uploads to storage (mocked)."""
        url = reverse_lazy("lost-customers-export")
        from unittest.mock import patch

        # Patch the STORAGE client used in the view to avoid a network call
        with (
            patch("apps.vendors.views.STORAGE.s3_client.put_object") as mock_put,
            patch(
                "apps.vendors.views.STORAGE.get_file_url",
                return_value="https://example.com/reports/lost.csv",
            ) as mock_get_url,
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data.get("data")
            # Should return url and filename even if list is empty
            self.assertIn("url", data)
            self.assertIn("filename", data)
            mock_put.assert_called()


class VendorWalletSummaryTest(TestCase):
    """Test the vendor wallet summary endpoint"""

    @classmethod
    def setUpTestData(cls):
        cls.vendor = CustomUser.objects.create_user(
            email="vendor@example.com", password="testpass"
        )
        cls.role = Role.objects.create(name="vendor")
        cls.vendor.roles.add(cls.role)

        # Create vendor wallet
        cls.wallet = VendorWallet.objects.create(
            vendor=cls.vendor, balance=Decimal("1000.00")
        )

        # Create buyer
        cls.buyer = CustomUser.objects.create_user(
            email="buyer@example.com", password="testpass"
        )

        # Create product
        cls.product = Product.objects.create(
            name="Product 1",
            price=Decimal("500.00"),
            stock_quantity=5,
            seller=cls.vendor,
        )

        # Create order and payment
        cls.order = Order.objects.create(
            buyer=cls.buyer, delivery_address="Test Street"
        )
        OrderItem.objects.create(order=cls.order, product=cls.product, quantity=2)

        # Paid payment
        cls.paid_payment = Payment.objects.create(
            user=cls.buyer,
            order=cls.order,
            amount=Decimal("1000.00"),
            payment_status=PaymentStatus.PAID,
            ref=f"TEST-{get_random_string(8)}",
        )

        # Pending payment
        cls.pending_order = Order.objects.create(
            buyer=cls.buyer, delivery_address="Another Street"
        )
        OrderItem.objects.create(
            order=cls.pending_order, product=cls.product, quantity=1
        )
        cls.pending_payment = Payment.objects.create(
            user=cls.buyer,
            order=cls.pending_order,
            amount=Decimal("500.00"),
            payment_status=PaymentStatus.PENDING,
            ref=f"TEST-{get_random_string(8)}",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.vendor)

    def test_wallet_summary(self):
        """Ensure wallet summary returns correct data"""
        url = reverse_lazy("vendor-wallet-metrics")
        response = self.client.get(url)
        print(response.data, "error form vendor-wllet")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        self.assertEqual(float(data["total_earned"]), 1000.00)
        self.assertEqual(float(data["pending"]), 500.00)
        self.assertEqual(float(data["available"]), 1000.00)
        self.assertEqual(float(data["withdrawn"]), 0.00)


class VendorExportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vendor = CustomUser.objects.create_user(
            email="vendor@example.com", password="test"
        )
        role = Role.objects.create(name="vendor")
        cls.vendor.roles.add(role)
        VendorWallet.objects.create(vendor=cls.vendor, balance=Decimal("0.00"))

        cls.buyer = CustomUser.objects.create_user(
            email="buyer@example.com", password="test"
        )
        cls.product = Product.objects.create(
            name="P", price=Decimal("100.00"), stock_quantity=10, seller=cls.vendor
        )

        # Create a few paid payments (small dataset)
        for i in range(3):
            order = Order.objects.create(buyer=cls.buyer, delivery_address=f"A{i}")
            OrderItem.objects.create(order=order, product=cls.product, quantity=1)
            Payment.objects.create(
                user=cls.buyer,
                order=order,
                amount=Decimal("100.00"),
                payment_status=PaymentStatus.PAID,
                ref=f"test-ref-paid-{i}",
            )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.vendor)

    def test_small_export_generates_file_and_notifies(self):
        """
        Small dataset should be exported synchronously.
        We patch:
          - apps.vendors.utils.upload_bytes_to_storage (the storage and exporter helper)
        so no network calls happen.
        """
        url = reverse_lazy("vendor-export")
        fake_url = "https://example.com/exports/fake.csv"
        # fake_path = "exports/fake.csv"

        from unittest.mock import patch

        # Patch the storage and export helper
        with (
            patch(
                "apps.vendors.utils.upload_bytes_to_storage", return_value=fake_url
            ) as mock_upload,
        ):
            response = self.client.post(
                url,
                {"export_format": "csv", "export_type": "transactions"},
                format="json",
            )

        print(response.data, "data frm test_small")

        # view returns 200 OK (synchronous small export)
        self.assertEqual(response.status_code, 200)

        payload = response.data.get("data")
        self.assertIn("url", payload, msg=f"Response missing url: {response.data}")
        self.assertEqual(payload["url"], fake_url)

        self.assertIn(
            "filename", payload, msg=f"Response missing filename: {response.data}"
        )

        # No ExportJob should be created for small sync export
        self.assertFalse(
            ExportJob.objects.exists(),
            "ExportJob exists but should not for small export",
        )

        # upload helper must have been called
        mock_upload.assert_called_once()
        self.assertTrue(mock_upload.called)

        # Notification created
        notices = Notification.objects.filter(
            user=self.vendor, notification_type="export_job"
        )
        self.assertTrue(
            notices.exists(), "No notification created for completed export"
        )

    def test_large_export_queues_job(self):
        """
        A large dataset (above VENDOR_EXPORT_QUEUE_THRESHOLD) should create an ExportJob
        and create a queued notification.
        """
        from django.conf import settings

        # get threshold from settings (it can be lowered via override_settings)
        threshold = getattr(settings, "VENDOR_EXPORT_QUEUE_THRESHOLD", 50)

        # create many records to exceed threshold
        for i in range(threshold + 2):
            order = Order.objects.create(buyer=self.buyer, delivery_address=f"big-{i}")
            OrderItem.objects.create(order=order, product=self.product, quantity=1)
            Payment.objects.create(
                user=self.buyer,
                order=order,
                amount=Decimal("100.00"),
                payment_status=PaymentStatus.PAID,
                ref=f"big-ref-{i}",
            )

        url = reverse_lazy("vendor-export")
        data = {"export_format": "csv"}

        response = self.client.post(url, data, format="json")
        print(response.data, "data frm test_large")

        self.assertIn(response.status_code, (200, 202))

        payload = response.data.get("data") or {}
        # job_id should be returned
        self.assertIn("job_id", payload, msg="Queued response did not return job_id")

        job_id = payload.get("job_id")
        self.assertTrue(
            ExportJob.objects.filter(
                id=job_id, user=self.vendor, status=ExportJob.STATUS_PENDING
            ).exists()
        )

        # A notification should have been created telling user export is queued
        notice = (
            Notification.objects.filter(
                user=self.vendor, notification_type="export_job"
            )
            .order_by("-created_at")
            .first()
        )
        self.assertIsNotNone(notice)
        self.assertIn("queued", notice.title.lower() + notice.message.lower())

        # job should be created
        self.assertTrue(
            ExportJob.objects.filter(
                user=self.vendor, status=ExportJob.STATUS_PENDING
            ).exists()
        )

    def test_processing_export_jobs_finishes_job_and_creates_notification(self):
        """
        Create a pending ExportJob, run management command, and assert:
          - job becomes COMPLETED
          - job.file is set
          - a completion notification was created
        Patch utils.upload_bytes_to_storage to avoid S3.
        """

        # create a pending job manually
        job = ExportJob.objects.create(
            user=self.vendor,
            export_type="transactions",
            export_format="csv",
            params={},
            status=ExportJob.STATUS_PENDING,
        )

        fake_url = "https://example.com/processed_fake.csv"

        from unittest.mock import patch

        # Patch upload helper used by the worker; worker calls create_export_file_for_vendor -> upload_bytes_to_storage
        with (
            patch(
                "apps.vendors.utils.upload_bytes_to_storage", return_value=fake_url
            ) as mock_upload,
        ):
            # Run management command that processes export jobs
            call_command("process_export_jobs")

        # refresh and re-fetch
        job.refresh_from_db()
        self.assertEqual(job.status, ExportJob.STATUS_COMPLETED)
        self.assertIsNotNone(job.completed_at)
        # file_name field should have been populated to the (fake) path
        self.assertTrue(
            bool(job.file_name), "Job file field not populated after processing"
        )
        # patched upload helper, ensure it was called
        mock_upload.assert_called()

        # A notification indicating "ready" or "download" should be created
        notice = (
            Notification.objects.filter(
                user=self.vendor, notification_type="export_job"
            )
            .order_by("-created_at")
            .first()
        )
        self.assertIsNotNone(notice)
        self.assertTrue(
            "ready" in (notice.title + notice.message).lower()
            or "download" in (notice.title + notice.message).lower()
        )


class AdminVendorControlsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # create roles
        cls.vendor_role = Role.objects.create(name="vendor")
        cls.user_role = Role.objects.create(name="user")

        # admin user (Django staff/superuser)
        cls.admin = CustomUser.objects.create_user(
            email="admin@example.com", password="adminpass"
        )
        cls.admin.is_staff = True
        cls.admin.is_superuser = True
        cls.admin.save()

        # vendor 1 (will have sales)
        cls.vendor1 = CustomUser.objects.create_user(
            email="seller1@example.com", password="vpass"
        )
        cls.vendor1.roles.add(cls.vendor_role)
        cls.vp1 = VendorsProfile.objects.create(
            user=cls.vendor1, business_name="Seller One"
        )

        # vendor 2 (no sales)
        cls.vendor2 = CustomUser.objects.create_user(
            email="seller2@example.com", password="vpass"
        )
        cls.vendor2.roles.add(cls.vendor_role)
        cls.vp2 = VendorsProfile.objects.create(
            user=cls.vendor2, business_name="Seller Two"
        )

        # buyer
        cls.buyer = CustomUser.objects.create_user(
            email="buyer@example.com", password="bpass"
        )
        cls.buyer.roles.add(cls.user_role)

        # product by vendor1
        cls.product = Product.objects.create(
            name="Prod", price=Decimal("100.00"), stock_quantity=10, seller=cls.vendor1
        )

        # an order & paid payment for vendor1
        cls.order = Order.objects.create(buyer=cls.buyer, delivery_address="Addr 1")
        OrderItem.objects.create(order=cls.order, product=cls.product, quantity=2)
        cls.payment = Payment.objects.create(
            user=cls.buyer,
            order=cls.order,
            amount=Decimal("200.00"),
            payment_status=PaymentStatus.PAID,
            ref="pay1",
        )

    def setUp(self):
        self.client = APIClient()

    def test_admin_can_view_global_stats_but_vendor_sees_own(self):
        # admin view
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse_lazy("vendor-stats"))
        self.assertEqual(response.status_code, 200)
        data = response.data.get("data")

        # global total vendors should include both vendors
        self.assertIn("total_vendors", data)
        self.assertGreaterEqual(data["total_vendors"], 2)
        self.client.force_authenticate(user=None)

        # vendor1 view - should only see own totals
        self.client.force_authenticate(user=self.vendor1)
        response2 = self.client.get(reverse_lazy("vendor-stats"))
        self.assertEqual(response2.status_code, 200)
        data2 = response2.data.get("data")

        # vendor sees only their totals: total_vendors should be omitted or equal to 1 depending on design.
        # We expect vendor to see "total_sales" and it should match vendor1's sales
        self.assertIn("total_sales", data2)
        self.assertNotIn("total_vendors", data2)

        self.assertEqual(float(data2["total_sales"]), 200.0)

    def test_only_admin_can_perform_vendor_actions(self):
        url = reverse_lazy("vendor-action", args=[str(self.vp2.id)])
        # vendor attempt should fail
        self.client.force_authenticate(user=self.vendor1)
        response = self.client.post(url, {"action": "suspend"}, format="json")
        print(response.data)
        print(response)
        self.assertEqual(response.status_code, 403)

        # admin can suspend
        self.client.force_authenticate(user=self.admin)
        response2 = self.client.post(
            url, {"action": "suspend", "reason": "policy"}, format="json"
        )
        self.assertEqual(response2.status_code, 200)
        # vendor2 profile should be suspended
        self.vp2.refresh_from_db()
        self.assertTrue(self.vp2.is_suspended)

        # audit log created
        log = AuditLog.objects.filter(
            action__icontains="suspend", target__icontains=str(self.vp2.id)
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.admin)
        # notification created for vendor
        notice = (
            Notification.objects.filter(user=self.vp2.user)
            .order_by("-created_at")
            .first()
        )
        self.assertIsNotNone(notice)
        self.assertIn("suspend", (notice.title + notice.message).lower())

    def test_admin_can_change_plan_and_it_is_logged(self):
        url = reverse_lazy("vendor-action", args=[str(self.vp1.id)])
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            url, {"action": "change_plan", "plan": "premium"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.vp1.refresh_from_db()
        self.assertEqual(self.vp1.plan_type, "premium")
        log = AuditLog.objects.filter(
            action__icontains="change_plan", target__icontains=str(self.vp1.id)
        ).first()
        self.assertIsNotNone(log)
