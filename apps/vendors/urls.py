from django.urls import path
from drf_spectacular.utils import extend_schema_view, extend_schema

from .views import (TotalSale,
                    TotalProduct,
                    SalesPerMonth,
                    LowStock,
                    NewCustomers,
                    CategoryDistribution, VendorAnalyticsView,
                    VendorProductView)


TotalSale = extend_schema_view(
    get=extend_schema(tags=["Vendors Dashboard"], summary="Get Total Sales")
)(TotalSale)
TotalProduct = extend_schema_view(
    get=extend_schema(tags=["Vendors Dashboard"], summary="Get Total Products")
)(TotalProduct)
SalesPerMonth = extend_schema_view(
    get=extend_schema(tags=["Vendors Dashboard"], summary="Get Sales Per Month")
)(SalesPerMonth)
LowStock = extend_schema_view(
    get=extend_schema(tags=["Vendors Dashboard"], summary="Get Low Stock Count")
)(LowStock)
NewCustomers = extend_schema_view(
    get=extend_schema(tags=["Vendors Dashboard"], summary="Get New Customers")
)(NewCustomers)
CategoryDistribution = extend_schema_view(
    get=extend_schema(tags=["Vendors Dashboard"], summary="Get Category Distribution")
)(CategoryDistribution)
VendorProductView = extend_schema_view(
    get=extend_schema(tags=["Vendors Dashboard"], summary="Get Vendor Product List")
)(VendorProductView)

urlpatterns = [
    path("products/", VendorProductView.as_view(), name="vendor-products"),
    path("totalsale/", TotalSale.as_view(), name="total-sale"),
    path("totalproduct/", TotalProduct.as_view(), name="total-product"),
    path("salespermonth/", SalesPerMonth.as_view(), name="total-sale-per-month"),
    path("lowstockcount/", LowStock.as_view(), name="low-stock-count"),
    path("newcustomers/", NewCustomers.as_view(), name="new-customers"),
    path("categorydistribution/", CategoryDistribution.as_view(), name="category-distribution"),
    path("vendor-analytics/", VendorAnalyticsView.as_view(), name="vendor-analytics"),
]
