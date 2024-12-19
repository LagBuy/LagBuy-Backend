from rest_framework.permissions import BasePermission


class IsSeller(BasePermission):
    """Custom permission to allow only sellers to access the view."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "seller"
