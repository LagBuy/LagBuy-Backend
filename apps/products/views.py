from rest_framework.authentication import TokenAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import logging

from common.utils.responses import error_response, success_response
from .models import Product
from .serializer import ProductSerializer

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
            return error_response("Internal server error",
                                  status.HTTP_500_INTERNAL_SERVER_ERROR)

        # if not request.user:
        #     return error_response("No permission to access this product",
        #                           status.HTTP_403_FORBIDDEN)

        serializer = ProductSerializer(product)
        return success_response(serializer.data,
                                "Product fetched successfully")

class GetAllProducts(APIView):
    """Get all products class"""

    def get(self, request, *args, **kwargs):
        """Method to fetch all products"""
        try:
            products = Product.objects.all()

            serializer = ProductSerializer(products, many=True)

            """Return structured success response"""
            return success_response(serializer.data,
                                    "Products fetched successfully")

        except Exception as e:
            """Log and return the exception details to the console"""
            logger.error(f"Internal server error: {str(e)}")
            print(f"Error occurred: {str(e)}")

            return error_response("Internal server error",
                                  status.HTTP_500_INTERNAL_SERVER_ERROR)

# class CreateProducts(APIView):
#     """Create product class"""
#
#     def create(self, request, *args, **kwargs):
#         """Create method for creating new product"""
#         try:
#             products = Product.objects.all()
#