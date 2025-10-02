import csv
import logging
from datetime import date, timedelta
from io import StringIO

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import F, Max, Min, OuterRef, Subquery
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.orders.models import OrderItem
from apps.products.serializers import ProductSerializer
from apps.userAuth.permissions import IsASeller
from common.services.storage import STORAGE
from common.utils.responses import error_response, success_response

from .utils import build_lost_customers_csv

logger = logging.getLogger(__name__)


class VendorProductView(APIView):
    """View to list all products of a vendor"""

    permission_classes = [IsAuthenticated, IsASeller]

    def get(self, request, *args, **kwargs):
        """List all products of the vendor"""
        try:
            seller = request.user
            products = seller.products.all()
            serializer = ProductSerializer(products, many=True)
            return success_response(
                data=serializer.data, message="Products of the vendor"
            )
        except PermissionDenied as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error while getting products of the vendor: {e}")
            return error_response(
                message="An error occurred while getting products of the vendor",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TotalSale(APIView):
    """Get total sales of the vendor"""

    permission_classes = [IsAuthenticated, IsASeller]

    def get(self, request, *args, **kwargs):
        """get total sales"""

        try:
            orderItems = OrderItem.objects.filter(
                order__payments__payment_status="paid", product__seller=request.user
            ).distinct()

            total_prices = sum([i.total_price for i in orderItems])

            return success_response(
                message="Total sales", data={"total_sale": total_prices}
            )
        except PermissionDenied as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error while getting total sale: {e}")
            return error_response(
                message="An error occurred while getting total sale",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TotalProduct(APIView):
    """Get total product a vendor has"""

    permission_classes = [IsAuthenticated, IsASeller]

    def get(self, request, *args, **kwargs):
        """get total product"""
        try:
            seller = request.user
            total = seller.products.all().count()
            return success_response(
                data={"total_product": total}, message="Total product"
            )
        except PermissionDenied as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error while getting total product: {e}")
            return error_response(
                message="An error occurred while getting total product",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NewCustomers(APIView):
    """Get the number of new customers purchasing from
    a seller in a specified number of days. Number of days
    can be specified using the query parameter `days`. Defaults to 30 days if not specified
    """

    permission_classes = [IsAuthenticated, IsASeller]

    def get(self, request, *args, **kwargs):
        days = request.query_params.get("days", 30)
        days = int(days)
        if days < 0:
            return error_response(
                message="Invalid number of days. Days can't be negative",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            days_ago = timezone.now() - timedelta(days=days)
            seller = request.user

            first_orders = (
                OrderItem.objects.filter(
                    product__seller=seller, order__buyer=OuterRef("order__buyer")
                )
                .order_by("order__created_at")
                .values("order__created_at")[:1]
            )
            new_customers = (
                OrderItem.objects.filter(
                    product__seller=seller, order__payments__payment_status="paid"
                )
                .annotate(first_order_date=Subquery(first_orders))
                .filter(first_order_date__gte=days_ago)
                .values(
                    "order__buyer__user_profile__first_name",
                    "order__buyer__user_profile__last_name",
                )
                .distinct()
                .annotate(
                    first_name=F("order__buyer__user_profile__first_name"),
                    last_name=F("order__buyer__user_profile__last_name"),
                )
                .values("first_name", "last_name")
            )
            new_customers_count = new_customers.count()

            return success_response(
                message=f"New customers in the {days} days",
                data={
                    "new_customers_count": new_customers_count,
                    "new_customers": new_customers,
                },
            )
        except PermissionDenied as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error while getting new customers info: {e}")
            return error_response(
                message="An error occurred while getting new customers info",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SalesPerMonth(APIView):
    """return a list for the total sales for each month for a year"""

    permission_classes = [IsAuthenticated, IsASeller]

    def get(self, request, *args, **kwargs):
        try:
            start_date = timezone.now() - relativedelta(years=1)
            start_date = start_date.replace(day=1)
            orderItems = OrderItem.objects.filter(
                order__payments__payment_status="paid",
                product__seller=request.user,
                order__created_at__gte=start_date,
            ).distinct()

            end_date = timezone.now()
            current_date = start_date
            data = {}
            while current_date <= end_date:
                next_month = current_date + relativedelta(months=1)

                # filter orders for each month
                orders_in_month = orderItems.filter(
                    order__created_at__gte=current_date,
                    order__created_at__lt=next_month,
                )

                key = current_date.strftime("%m-%Y")
                data[key] = sum([i.total_price for i in orders_in_month])

                current_date = next_month

            return success_response(message="Sales per month", data=data)
        except PermissionDenied as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error while getting total sales per month: {e}")
            return error_response(
                message="An error occurred while getting total sales per month",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LowStock(APIView):
    """Get count of products with low stock (stock quantity less than 5 by default or
    any quantity you set using the query parameter `lt`)"""

    permission_classes = [IsAuthenticated, IsASeller]

    def get(self, request, *args, **kwargs):
        lt = request.query_params.get("lt", 5)
        lt = int(lt)

        try:
            seller = request.user
            low_stock = seller.products.filter(stock_quantity__lt=lt).values(
                "name", "stock_quantity"
            )
            low_stock_count = low_stock.count()

            return success_response(
                message="Low Stock (products with stock quantity less than `lt` query argument, defaults to 5)",
                data={
                    "low_stock_products": low_stock,
                    "low_stock_count": low_stock_count,
                },
            )
        except PermissionDenied as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error while getting Low stock count: {e}")
            return error_response(
                message="An error occurred while getting Low stock count",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CategoryDistribution(APIView):
    """Get the category distribution of the vendor products"""

    permission_classes = [IsAuthenticated, IsASeller]

    def get(self, request, *args, **kwargs):
        try:
            seller = request.user
            products = seller.products.all()
            categories = []
            for product in products:
                categories += product.categories.all()
            categories_name = [i.name for i in categories]

            total = len(categories_name)
            """Get the ratio of the categories across all products"""
            categories = {}
            for i in set(categories_name):
                categories[i] = categories_name.count(i)

            distribution = {i: (j / total) * 100 for i, j in categories.items()}
            return success_response(
                data=distribution, message="Product Category Distribution in %"
            )
        except PermissionDenied as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error while getting Category distribution: {e}")
            return error_response(
                message="An error occurred while getting Category distribution",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CustomersOverview(APIView):
    """Provide customer metrics for a vendor: new today, active (within N days), lost (>N days), and growth chart."""

    permission_classes = [IsAuthenticated, IsASeller]

    def get(self, request, *args, **kwargs):
        try:
            seller = request.user
            days = int(request.query_params.get("days", 90))
            chart_days = int(request.query_params.get("chart_days", 30))
            if days < 0 or chart_days <= 0:
                return error_response(
                    message="Invalid query parameters for days or chart_days",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            cutoff = timezone.now() - timedelta(days=days)

            # Aggregate per buyer their first and last purchase with this seller
            buyers = (
                OrderItem.objects.filter(
                    product__seller=seller, order__payments__payment_status="paid"
                )
                .values("order__buyer")
                .annotate(
                    first_purchase=Min("order__created_at"),
                    last_purchase=Max("order__created_at"),
                )
            )

            # New customers today
            today = timezone.now().date()
            new_today_count = buyers.filter(first_purchase__date=today).count()

            # Active customers (bought within `days`)
            active_count = buyers.filter(last_purchase__gte=cutoff).count()

            # Lost customers (last purchase before cutoff)
            lost_qs = buyers.filter(last_purchase__lt=cutoff)
            lost_count = lost_qs.count()

            # Growth chart: new customers per day for chart_days
            chart = []
            for i in range(chart_days - 1, -1, -1):
                d = (timezone.now() - timedelta(days=i)).date()
                count = buyers.filter(first_purchase__date=d).count()
                chart.append({"date": d.isoformat(), "new_customers": count})

            return success_response(
                message="Customer overview",
                data={
                    "new_customers_today": new_today_count,
                    "active_customers_count": active_count,
                    "lost_customers_count": lost_count,
                    "growth_chart": chart,
                },
            )
        except Exception as e:
            logger.exception(f"Error generating customer overview: {e}")
            return error_response(
                message="Error generating customer overview",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LostCustomersExport(APIView):
    """Export lost customers (no purchase in `days`) as CSV."""

    permission_classes = [IsAuthenticated, IsASeller]

    def get(self, request, *args, **kwargs):
        try:
            seller = request.user
            days = int(request.query_params.get("days", 90))
            if days < 0:
                return error_response(
                    message="Invalid number of days. Days can't be negative",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            cutoff = timezone.now() - timedelta(days=days)

            buyers = (
                OrderItem.objects.filter(
                    product__seller=seller, order__payments__payment_status="paid"
                )
                .values("order__buyer")
                .annotate(last_purchase=Max("order__created_at"))
            )

            lost_ids = [
                b["order__buyer"] for b in buyers.filter(last_purchase__lt=cutoff)
            ]

            # Fetch user data
            from apps.userAuth.models import CustomUser

            users = CustomUser.objects.filter(id__in=lost_ids).select_related(
                "user_profile"
            )

            # Map last_purchase by user id
            last_map = {
                b["order__buyer"]: b["last_purchase"]
                for b in buyers.filter(last_purchase__lt=cutoff)
            }

            # Build CSV bytes using helper
            csv_bytes = build_lost_customers_csv(users, last_map)
            filename = f"reports/lost_customers_{seller.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.csv"
            try:
                STORAGE.s3_client.put_object(
                    Bucket=STORAGE.bucket_name,
                    Key=filename,
                    Body=csv_bytes,
                    ContentType="text/csv",
                )
                file_url = STORAGE.get_file_url(filename)
                return success_response(
                    message="Lost customers CSV uploaded",
                    data={"url": file_url, "filename": filename},
                )
            except Exception as e:
                logger.exception(f"Error uploading lost customers CSV to S3: {e}")
                return error_response(
                    message="Error uploading CSV to storage",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        except Exception as e:
            logger.exception(f"Error exporting lost customers: {e}")
            return error_response(
                message="Error exporting lost customers",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def build_lost_customers_csv(users, last_map):
    """Return CSV bytes for given users and last_purchase mapping.

    Args:
        users: iterable of CustomUser objects (with optional user_profile relation)
        last_map: dict mapping user id -> last_purchase datetime

    Returns:
        bytes: UTF-8 encoded CSV bytes
    """
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["id", "email", "first_name", "last_name", "last_purchase"])
    for u in users:
        lp = last_map.get(str(u.id)) or last_map.get(u.id)
        writer.writerow(
            [
                str(u.id),
                u.email,
                getattr(getattr(u, "user_profile", None), "first_name", ""),
                getattr(getattr(u, "user_profile", None), "last_name", ""),
                lp.isoformat() if lp is not None else "",
            ]
        )
    return csv_buffer.getvalue().encode("utf-8")
