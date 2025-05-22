from django.urls import path

from .views import (TotalSale,
                    TotalProduct,
                    SalesPerMonth,
                    LowStock,
                    NewCustomers,
                    CategoryDistribution)

urlpatterns = [
    path("totalsale/", TotalSale.as_view(), name="total-sale"),
    path("totalproduct/", TotalProduct.as_view(), name="total-product"),
    path("salespermonth/", SalesPerMonth.as_view(), name="total-sale-graph"),
    path("lowstockcount/", LowStock.as_view(), name="low-stock-count"),
    path("newcustomers/", NewCustomers.as_view(), name="new-customers"),
    path("categorydistribution/", CategoryDistribution.as_view(), name="category-distribution"),
]
