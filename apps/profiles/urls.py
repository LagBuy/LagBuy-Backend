from django.urls import path
from drf_spectacular.utils import extend_schema_view, extend_schema

from .views import ViewVendorProfileViewSet, FavouriteVendor

ViewVendorProfileViewSet = extend_schema_view(
    list=extend_schema(tags=["Profiles"], summary="List Vendor Profiles"),
    retrieve=extend_schema(tags=["Profiles"], summary="Retrieve Vendor Profile"),
)(ViewVendorProfileViewSet)
FavouriteVendor = extend_schema_view(
    list=extend_schema(tags=["Profiles"], summary="List Favorite Vendors"),
    create=extend_schema(tags=["Profiles"], summary="Add Favorite Vendor"),
    destroy=extend_schema(tags=["Profiles"], summary="Remove Favorite Vendor"),
)(FavouriteVendor)

vendor_profile_list = ViewVendorProfileViewSet.as_view({'get': 'list'})
vendor_profile_detail = ViewVendorProfileViewSet.as_view({'get': 'retrieve'})
favourite_vendor_list = FavouriteVendor.as_view({'get': 'list', 'post': 'create'})
favourite_vendor_detail = FavouriteVendor.as_view({'delete': 'destroy'})

urlpatterns = [
    path("vendors/", vendor_profile_list, name="vendor-profile-list"),
    path("vendors/<uuid:user__id>/", vendor_profile_detail, name="vendor-profile-detail"),
    path("vendors/favorites/", favourite_vendor_list, name="favourite-vendor-list"),
    path("vendors/favorites/<uuid:vendor_id>/", favourite_vendor_detail, name="favourite-vendor-detail"),
]
