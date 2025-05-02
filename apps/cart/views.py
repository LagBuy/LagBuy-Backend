from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated

from common.utils.responses import error_response, success_response

from .models import Cart, CartItem
from .serializers import CartItemSerializer, CartSerializer


class CartViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset for managing the user's cart.
    Only allows retrieving the current user's cart.
    """
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "delete"]

    def get_queryset(self):
        # Only allow users to access their own cart
        return self.queryset.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """
        Retrieve the current user's cart.
        If the cart does not exist, create it.
        """
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return success_response(serializer.data, "Cart retrieved successfully.")

    def destroy(self, request, *args, **kwargs):
        """
        Allow users to clear their cart by deleting all items.
        """
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return error_response("Cart not found.", status.HTTP_404_NOT_FOUND)
        cart.items.all().delete()
        return success_response({}, "Cart cleared successfully.", status.HTTP_204_NO_CONTENT)

class CartItemViewSet(viewsets.ModelViewSet):
    """
    Viewset for managing items in the user's cart.
    Allows listing, adding, updating, and removing cart items.
    """
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "delete"]

    def get_queryset(self):
        # Only allow users to access items in their own cart
        cart = Cart.objects.filter(user=self.request.user).first()
        if not cart:
            return CartItem.objects.none()
        return self.queryset.filter(cart=cart)

    def list(self, request, *args, **kwargs):
        """
        List all items in the current user's cart.
        """
        queryset = self.get_queryset()
        serializer = CartItemSerializer(queryset, many=True)
        return success_response(serializer.data, "Cart items retrieved successfully.")

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific cart item.
        """
        instance = self.get_object()
        serializer = CartItemSerializer(instance)
        return success_response(serializer.data, "Cart item retrieved successfully.")

    def create(self, request, *args, **kwargs):
        """
        Add a new item to the user's cart or update quantity if it exists.
        """
        cart, _ = Cart.objects.get_or_create(user=request.user)
        data = request.data.copy()
        data["cart"] = cart.id

        # Check if item already exists in cart
        existing_item = CartItem.objects.filter(
            cart=cart, product=data.get("product"),
        ).first()
        if existing_item:
            existing_item.quantity += int(data.get("quantity", 1))
            existing_item.save()
            serializer = CartItemSerializer(existing_item)
            return success_response(
                serializer.data, "Cart item quantity updated.", status.HTTP_200_OK
            )

        serializer = CartItemSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return success_response(
                serializer.data,
                "Cart item added successfully.",
                status.HTTP_201_CREATED,
            )
        return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        Update the quantity or details of a cart item.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = CartItemSerializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return success_response(serializer.data, "Cart item updated successfully.")
        return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        Remove an item from the user's cart.
        """
        instance = self.get_object()
        instance.delete()
        return success_response(
            {}, "Cart item removed successfully.", status.HTTP_204_NO_CONTENT
        )