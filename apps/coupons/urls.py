from django.urls import path

from .views import (CouponDetailView,
                    CouponListView,
                    SellerCouponDetailUpdateDeleteView,
                    SellerCouponListCreateView,
                    VerifyCouponView)

urlpatterns = [
    path("", CouponListView.as_view(), name="admin-coupons-list"),     # for admin user
    path("seller/", SellerCouponListCreateView.as_view(), name="coupon-list"),
    path("seller/<str:code>/", SellerCouponDetailUpdateDeleteView.as_view(), name="coupon-detail"),
    path("verify/", VerifyCouponView.as_view(), name="verify-coupon"),
    path("<str:code>/", CouponDetailView.as_view(), name="admin-coupon-detail"),      # for admin user
]
