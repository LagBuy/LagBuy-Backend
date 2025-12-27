from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import generics

from apps.userAuth.permissions import IsASeller
from common.utils.responses import customize_response, success_response, error_response
from apps.userAuth.models import CustomUser
from .serializer import VendorProfileSerializer, VendorBankDetailsUpdateSerializer
from .models import VendorsProfile

# TODO: create a view to see individual users detail (vendor and admin only)
# TODO: create a view to see all users (admin only)


class ViewVendorProfileViewSet(ReadOnlyModelViewSet):
    """A viewset to view vendor profile"""

    serializer_class = VendorProfileSerializer
    queryset = VendorsProfile.objects.order_by("-business_name")
    permission_classes = [AllowAny]
    http_method_names = ["get"]
    lookup_field = "user__id"  # Use user ID for lookups instead of profile ID

    def list(self, request, *args, **kwargs):
        """Get list of all vendor profiles"""
        response = super().list(request, *args, **kwargs)
        return customize_response(response, "Vendor profiles retrieved successfully")

    def retrieve(self, request, *args, **kwargs):
        """Get a single vendor profile"""
        response = super().retrieve(request, *args, **kwargs)
        return customize_response(response, "Vendor profile retrieved successfully")


class FavouriteVendor(ModelViewSet):
    """A viewset to manage user's favorite vendors"""

    serializer_class = VendorProfileSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]
    queryset = VendorsProfile.objects.all()

    def get_queryset(self):
        user = self.request.user
        return VendorsProfile.objects.filter(
            user__in=user.user_profile.favorite_vendors.all()
        )  # .select_related('user')

    def list(self, request, *args, **kwargs):
        """Get list of user's favorite vendors"""
        response = super().list(request, *args, **kwargs)
        return customize_response(response, "Favorite vendors retrieved successfully")

    def create(self, request, *args, **kwargs):
        """Add a vendor to user's favorite vendors"""
        vendor_id = request.data.get("vendor_id")
        try:
            vendor = CustomUser.objects.get(id=vendor_id, roles__name="vendor")
            request.user.user_profile.favorite_vendors.add(vendor)
            return success_response(
                None, "Vendor added to favorites successfully", status_code=201
            )
        except CustomUser.DoesNotExist:
            return error_response("Vendor not found", status_code=404)

    def destroy(self, request, vendor_id, *args, **kwargs):
        """Remove a vendor from user's favorite vendors"""
        vendor_id = vendor_id
        try:
            vendor = CustomUser.objects.get(id=vendor_id, roles__name="vendor")
            request.user.user_profile.favorite_vendors.remove(vendor)
            return success_response(
                None, "Vendor removed from favorites successfully", status_code=204
            )
        except CustomUser.DoesNotExist:
            return error_response("Vendor not found", status_code=404)


class UpdateVendorBankDetailsView(generics.UpdateAPIView):
    serializer_class = VendorBankDetailsUpdateSerializer
    permission_classes = [IsAuthenticated, IsASeller]

    def get_object(self):
        return self.request.user.vendor_profile


class CheckBusinessNameExists(ModelViewSet):
    """a view to check if a business name already exists"""
    serializer_class = VendorProfileSerializer
    permission_classes = [AllowAny]
    http_method_names = ["get"]
    queryset = VendorsProfile.objects.all()

    def list(self, request, *args, **kwargs):
        """Check if business name exists"""
        business_name = request.query_params.get("business_name", None)
        if business_name is None:
            return error_response(
                "business_name query parameter is required", status_code=400
            )
        exists = VendorsProfile.objects.filter(business_name__iexact=business_name).exists()
        data = {"business_name": business_name, "exists": exists}
        return success_response(data, "Business name existence checked successfully")
