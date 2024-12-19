from django.urls import path

from .views import CouponDetailView, CouponListView, SellerCouponDetailUpdateDeleteView, SellerCouponListCreateView, VerifyCouponView

urlpatterns = [
    path("", CouponListView.as_view(), name="coupons"),
    path("seller/", SellerCouponListCreateView.as_view(), name="seller-coupon-detail"),
    path("seller/<str:code>/", SellerCouponDetailUpdateDeleteView.as_view(), name="seller-coupons"),
    path("verify/", VerifyCouponView.as_view(), name="verify-coupon"),
    path("<str:code>/", CouponDetailView.as_view(), name="coupon-detail"),
]
