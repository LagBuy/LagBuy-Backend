from django.urls import path
from drf_spectacular.utils import extend_schema_view, extend_schema

from .views import (CouponDetailView,
                    CouponListView,
                    SellerCouponDetailUpdateDeleteView,
                    SellerCouponListCreateView,
                    VerifyCouponView)

CouponListView = extend_schema_view(
    get=extend_schema(tags=["Coupons"], summary="List All Coupons"),
)(CouponListView)
CouponDetailView = extend_schema_view(
    get=extend_schema(tags=["Coupons"], summary="Retrieve Coupon Details"),
)(CouponDetailView)
SellerCouponListCreateView = extend_schema_view(
    get=extend_schema(tags=["Coupons"], summary="List Seller Coupons"),
    post=extend_schema(tags=["Coupons"], summary="Create a New Coupon"),
)(SellerCouponListCreateView)
SellerCouponDetailUpdateDeleteView = extend_schema_view(
    get=extend_schema(tags=["Coupons"], summary="Retrieve Seller Coupon Details"),
    put=extend_schema(tags=["Coupons"], summary="Update Seller Coupon"),
    delete=extend_schema(tags=["Coupons"], summary="Delete Seller Coupon"),
)(SellerCouponDetailUpdateDeleteView)
VerifyCouponView = extend_schema_view(
    post=extend_schema(tags=["Coupons"], summary="Verify Coupon Code"),
)(VerifyCouponView) 

urlpatterns = [
    path("", CouponListView.as_view(), name="admin-coupons-list"),     # for admin user
    path("seller/", SellerCouponListCreateView.as_view(), name="coupon-list"),
    path("seller/<str:code>/", SellerCouponDetailUpdateDeleteView.as_view(), name="coupon-detail"),
    path("verify/", VerifyCouponView.as_view(), name="verify-coupon"),
    path("<str:code>/", CouponDetailView.as_view(), name="admin-coupon-detail"),      # for admin user
]
