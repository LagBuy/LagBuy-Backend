from rest_framework import permissions
from apps.userAuth.models import Role


class IsOwnerBuyer(permissions.BasePermission):
    """A permission class to allow only
    the owner(buyer) of an object to access/update it.
    In cases where the assinged 'owner' of an object is
    a buyer (Review, Order, etc), this permission class should be used
    """

    def has_permission(self, request, view):
        """Ensure the user is logged in"""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Ensure that the logged in user is the owner of the object"""
        return obj.buyer == request.user


class IsOwnerSeller(permissions.BasePermission):
    """A permission class to allow only
    the seller of a product to access/update it.
    In cases where the assinged 'owner' of an object is
    a seller (Product, Coupon, etc), this permission class should be used
    """

    def has_permission(self, request, view):
        """Ensure the user is logged in"""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Ensure that the logged in user is the seller"""
        return obj.seller == request.user


class IsASeller(permissions.BasePermission):
    """A permission class to allow only
    the seller of a product to access/update it.
    In cases where the assinged 'owner' of an object is
    a seller (Product, Coupon, etc), this permission class should be used
    """

    def has_permission(self, request, view):
        """Ensure the user is logged in"""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Ensure that the logged in user is the seller"""
        return obj.seller == request.user
    

class IsASeller(permissions.BasePermission):
    """
    Allows access only to users with the 'seller' role.
    Use this permission to restrict actions (like product creation) to sellers only.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and 'vendor' in [i.name for i in request.user.roles.all()]
        )

# TODO: update all permission to reflect the update
