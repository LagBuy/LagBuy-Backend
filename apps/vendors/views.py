import logging

from dateutil.relativedelta import relativedelta
from datetime import timedelta

from django.utils import timezone
from django.db.models import OuterRef, Subquery, F
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from common.utils.responses import success_response, error_response
from apps.products.models import Product
from apps.orders.models import OrderItem, Order
from apps.userauth.permissions import IsOwnerSeller, IsASeller


logger = logging.getLogger(__name__)

class TotalSale(APIView):
    """Get total sales of the seller"""
    permission_classes = [IsAuthenticated, IsASeller]

    def get(self, request, *args, **kwargs):
        """get total sales"""

        try:
            # TODO: Test to ensure only a seller can access this.
            orderItems = OrderItem.objects.filter(
                order__payment_status=Order.PaymentStatus.PAID,
                product__seller = request.user)

            total_prices = sum([i.total_price for i in orderItems])

            return success_response(
                message="Total sales",
                data = {"total_sale": total_prices}
            )
        except PermissionDenied as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error while getting total sale: {e}")
            return error_response(
                message="An error occurred while getting total sale",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TotalProduct(APIView):
    """Get total product a seller has"""
    permission_classes = [IsAuthenticated, IsASeller]

    def get(self, request, *args, **kwargs):
        '''get total product'''
        try:
            seller = request.user
            total = seller.products.all().count()
            return success_response(
                data={'total_product': total},
                message="Total product"
            )
        except PermissionDenied as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error while getting total product: {e}")
            return error_response(
                message="An error occurred while getting total product",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
class NewCustomers(APIView):
    """Get the number of new customers purchasing from
    a seller in the past 30 days"""
    permission_classes = [IsAuthenticated, IsASeller]

    def get(self, request, *args, **kwargs):
        
        try:
            one_month_ago = timezone.now() - timedelta(days=30)
            seller = request.user

            first_orders = (OrderItem.objects
                            .filter(product__seller=seller, order__buyer=OuterRef('order__buyer'))
                            .order_by('order__created_at')
                            .values('order__created_at')[:1]
                            )
            new_customers = (
                OrderItem.objects
                .filter(product__seller=seller)
                .annotate(first_order_date=Subquery(first_orders))
                .filter(first_order_date__gte=one_month_ago)
                .values('order__buyer__first_name', 'order__buyer__last_name')
                .distinct()
                .annotate(first_name=F('order__buyer__first_name'), last_name=F('order__buyer__last_name'))
                .values('first_name', 'last_name')
            )
            new_customers_count = new_customers.count()

            return success_response(
                    message="New customers in the past month",
                    data = {
                        'new_customers_count': new_customers_count,
                        'new_customers': new_customers,
                    }
                )
        except PermissionDenied as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error while getting new customers info: {e}")
            return error_response(
                message="An error occurred while getting new customers info",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SalesPerMonth(APIView):
    """return a list for the total sales for each month for a year"""
    permission_classes = [IsAuthenticated, IsASeller]

    def get(self, request, *args, **kwargs):

        try:
            start_date = timezone.now() - relativedelta(years=1)
            start_date = start_date.replace(day=1)
            orderItems = OrderItem.objects.filter(
                    order__payment_status=Order.PaymentStatus.PAID,
                    product__seller = request.user,
                    order__created_at__gte=start_date
                    )
            
            end_date = timezone.now()
            current_date = start_date
            data = {}
            while current_date <= end_date:
                next_month = current_date + relativedelta(months=1)

                # filter orders for each month
                orders_in_month = orderItems.filter(
                    order__created_at__gte=current_date,
                    order__created_at__lt=next_month
                )

                key = current_date.strftime("%m-%Y")
                data[key] = sum([i.total_price for i in orders_in_month])

                current_date = next_month
            
            return success_response(
                    message="Sales per month",
                    data = data
                )
        except PermissionDenied as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error while getting total sales per month: {e}")
            return error_response(
                message="An error occurred while getting total sales per month",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LowStock(APIView):
    """Get count of products with low stock (stock quantity less than 5)"""

    permission_classes = [IsAuthenticated, IsASeller]
    def get(self, request, *args, **kwargs):

        try:
            seller = request.user
            low_stock = seller.products.filter(stock_quantity__lt=5).values(
                'name', 'stock_quantity')
            low_stock_count = low_stock.count()

            return success_response(
                    message="Low Stock (products with stock quantity less than 5)",
                    data = {
                        "low_stock_products": low_stock,
                        "low_stock_count": low_stock_count,
                        }
                )
        except PermissionDenied as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error while getting Low stock count: {e}")
            return error_response(
                message="An error occurred while getting Low stock count",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
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

            distribution = {i: (j/total)*100 for i, j in categories.items()}            
            return success_response(
                data=distribution,
                message="Product Category Distribution in %"
            )
        except PermissionDenied as e:
            return error_response(
                message=e.detail, status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error while getting Category distribution: {e}")
            return error_response(
                message="An error occurred while getting Category distribution",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )