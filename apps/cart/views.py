from rest_framework import status, viewsets
from rest_framework.decorators import action
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
    http_method_names = ["get", "post", "delete"]

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

    @action(detail=False, methods=["post"])
    def add_item(self, request, *args, **kwargs):
        """
        Add an item to the user's cart. If the item exists, update its quantity based on the request:
        - If quantity is provided, replace the existing quantity.
        - If quantity is not provided, increment the existing quantity by one.
        If the item does not exist, create it with the provided quantity or default to 1.
        """
        try:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            product_id = request.data.get("product")
            quantity = request.data.get("quantity")
            if not product_id:
                return error_response(
                    "Product ID is required.", status.HTTP_400_BAD_REQUEST
                )

            cart_item = cart.items.filter(product_id=product_id).first()
            if cart_item:
                # If item exists, update quantity accordingly
                if quantity is not None:
                    try:
                        quantity = int(quantity)
                    except (ValueError, TypeError):
                        return error_response(
                            "Quantity must be an integer.", status.HTTP_400_BAD_REQUEST
                        )
                    if quantity <= 0:
                        return error_response(
                            "Quantity must be greater than zero.", status.HTTP_400_BAD_REQUEST
                        )
                    cart_item.quantity = quantity  # Replace with provided quantity
                else:
                    cart_item.quantity += 1  # Increment by one if not provided
                cart_item.save()
                serializer = CartItemSerializer(cart_item)
                return success_response(
                    serializer.data,
                    "Cart item quantity updated.",
                    status.HTTP_200_OK,
                )
            # If item does not exist, create new with provided quantity or default to 1
            data = request.data.copy()
            data["cart"] = cart.id
            if quantity is not None:
                try:
                    quantity = int(quantity)
                except (ValueError, TypeError):
                    return error_response(
                        "Quantity must be an integer.", status.HTTP_400_BAD_REQUEST
                    )
                if quantity <= 0:
                    return error_response(
                        "Quantity must be greater than zero.", status.HTTP_400_BAD_REQUEST
                    )
                data["quantity"] = quantity
            else:
                data["quantity"] = 1
            serializer = CartItemSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    serializer.data,
                    "Cart item added successfully.",
                    status.HTTP_201_CREATED,
                )
            return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["delete"])
    def remove_item(self, request, *args, **kwargs):
        """
        Remove an item from the user's cart.
        """
        try:
            cart = Cart.objects.filter(user=request.user).first()
            if not cart:
                return error_response("Cart not found.", status.HTTP_404_NOT_FOUND)

            item_id = request.data.get("item_id")
            if not item_id:
                return error_response(
                    "Item ID is required.", status.HTTP_400_BAD_REQUEST
                )

            cart_item = cart.items.get(id=item_id)
            cart_item.delete()
            return success_response({}, "Cart item removed successfully.")
        except CartItem.DoesNotExist:
            return error_response("Cart item not found.", status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        Allow users to clear their cart by deleting all items.
        """
        try:
            cart = Cart.objects.filter(user=request.user).first()
            if not cart:
                return error_response("Cart not found.", status.HTTP_404_NOT_FOUND)
            cart.items.all().delete()
            return success_response(
                {}, "Cart cleared successfully.", status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)


class CartItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset for managing items in the user's cart.
    Allows listing and retrieving cart items only. Add/remove/update via CartViewSet actions.
    """

    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

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
