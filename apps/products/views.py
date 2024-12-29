import logging

from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils.responses import error_response, success_response

from .models import Product
from .serializer import InventoryUpdateSerializer, ProductSerializer

logger = logging.getLogger(__name__)


class GetProduct(APIView):
    """Get product by ID class"""

    authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        """Get method for fetching products by ID"""
        if not id:
            return error_response("No ID provided", status.HTTP_400_BAD_REQUEST)

        """Try to retrieve the product and
        handle any potential internal errors"""
        try:
            product = Product.objects.get(id=id)
        except Product.DoesNotExist:
            return error_response("Product not found", status.HTTP_404_NOT_FOUND)
        except Exception as e:
            """Log the exception details to the console"""
            logger.error(f"Internal server error: {str(e)}")
            print(f"Error occurred: {str(e)}")

            """Return the structured error response with
            500 status code for internal errors"""
            return error_response(
                "Internal server error", status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # if not request.user:
        #     return error_response("No permission to access this product",
        #                           status.HTTP_403_FORBIDDEN)

        serializer = ProductSerializer(product)
        return success_response(serializer.data, "Product fetched successfully")


class GetAllProducts(APIView):
    """Get all products class"""

    def get(self, request, *args, **kwargs):
        """Method to fetch all products"""
        try:
            products = Product.objects.all()

            serializer = ProductSerializer(products, many=True)

            """Return structured success response"""
            return success_response(serializer.data, "Products fetched successfully")

        except Exception as e:
            """Log and return the exception details to the console"""
            logger.error(f"Internal server error: {str(e)}")
            print(f"Error occurred: {str(e)}")

            return error_response(
                "Internal server error", status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateProductStock(APIView):
    """Update stock of a product"""

    permission_classes = [IsAuthenticated]

    def post(self, request, id, *args, **kwargs):
        """Method to update stock of a product"""
        try:
            product = Product.objects.get(id=id)
            serializer = InventoryUpdateSerializer(data=request.data)
            if serializer.is_valid():
                new_quantity = (
                    product.stock_quantity + serializer.validated_data["quantity"]
                )
                if new_quantity < 0:
                    return error_response(
                        message="Insufficient stock.",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
                product.stock_quantity = new_quantity
                product.save()
                return success_response(
                    {"stock_quantity": product.stock_quantity},
                    "Stock updated successfully",
                )
            return error_response(
                message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Product.DoesNotExist:
            return error_response("Product not found", status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating stock: {e}")
            return error_response(
                message="An error occurred while updating stock.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
