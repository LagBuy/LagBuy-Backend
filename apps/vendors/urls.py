from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view

from .views import (
    CategoryDistribution,
    CustomersOverview,
    LostCustomersExport,
    LowStock,
    NewCustomers,
    SalesPerMonth,
    TotalProduct,
    TotalSale,
    VendorProductView,
    VendorSalesReport,
)

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
CustomersOverview = extend_schema_view(
    get=extend_schema(tags=["Vendors Dashboard"], summary="Get Customers Overview")
)(CustomersOverview)
LostCustomersExport = extend_schema_view(
    get=extend_schema(tags=["Vendors Dashboard"], summary="Export Lost Customers CSV")
)(LostCustomersExport)

VendorSalesReport = extend_schema_view(
    get=extend_schema(tags=["Vendors Dashboard"], summary="Get Vendor Sales Report")
)(VendorSalesReport)

urlpatterns = [
    path("products/", VendorProductView.as_view(), name="vendor-products"),
    path("totalsale/", TotalSale.as_view(), name="total-sale"),
    path("totalproduct/", TotalProduct.as_view(), name="total-product"),
    path("salespermonth/", SalesPerMonth.as_view(), name="total-sale-per-month"),
    path("lowstockcount/", LowStock.as_view(), name="low-stock-count"),
    path("newcustomers/", NewCustomers.as_view(), name="new-customers"),
    path("customers-overview/", CustomersOverview.as_view(), name="customers-overview"),
    path(
        "lost-customers-export/",
        LostCustomersExport.as_view(),
        name="lost-customers-export",
    ),
    path(
        "categorydistribution/",
        CategoryDistribution.as_view(),
        name="category-distribution",
    ),
    path("sales-report/", VendorSalesReport.as_view(), name="vendor-sales-report"),
]
