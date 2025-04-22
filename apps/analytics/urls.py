from django.urls import path

from .views import TotalSale

urlpatterns = [
    path("totalsale", TotalSale.as_view(), name="totalsale"),
]
