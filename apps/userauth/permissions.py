from rest_framework import permissions

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

class IsBuyer(IsOwnerBuyer):
    """To allow for backward compactibility,
    for any view that already use previous name"""
    pass

class IsSeller(IsOwnerSeller):
    """To allow for backward compactibility,
    for any view that already use previous name"""
    pass
