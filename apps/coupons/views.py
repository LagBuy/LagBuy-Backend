import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import PermissionDenied

from .models import Coupon
from .serializers import CouponSerializer, CouponBuyerSerializer
from common.utils.responses import success_response, error_response
from apps.userauth.permissions import IsOwnerSeller
from apps.products.models import Product

logger = logging.getLogger(__name__)


class VerifyCouponView(APIView):
    """Verify the validity of a coupon on a product"""
    def get(self, request, *args, **kwargs):
        """Return a success or error response
        if the coupon is valid or not"""
        data = request.data
        if not data:
            return error_response("No data provided",
                                  status.HTTP_400_BAD_REQUEST)
        
        code = data.get('code', None)
        product_id = data.get('product_id', None)
        quantity = data.get('quantity', None)
        if not code:
            return error_response("NO coupon code provided", status.HTTP_400_BAD_REQUEST)
        elif not product_id:
            return error_response("Product ID not provided", status.HTTP_400_BAD_REQUEST)
        elif not quantity:
            return error_response("Specify the quatity the user is buying", status.HTTP_400_BAD_REQUEST)
        
        try:
            """get coupon and product"""
            coupon = Coupon.objects.get(code=code)
            product = Product.objects.get(id=product_id)
        except Coupon.DoesNotExist:
            return error_response("Invalid coupon code", status.HTTP_404_NOT_FOUND)
        except Product.DoesNotExist:
            return error_response("Product not found", status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Internal Server Error while verifying coupon: {str(e)}")
            print(f"Error while verifying coupon: {str(e)}")
            return error_response("Internal Server Error",
                                  status.HTTP_500_INTERNAL_SERVER_ERROR)
        if not coupon.status:
                return error_response(
                    "Coupon has either expired or has reached it's usage limit",
                    status_code=status.HTTP_400_BAD_REQUEST
                    )
        """Ensure that the coupon is valid for the product it is applied on"""
        coupon_products = coupon.products
        if product in coupon_products:
            if not coupon.min_purchase_quantity and not coupon.max_purchase_quantity:
                if coupon.min_purchase_quantity < quantity or quantity > coupon.max_purchase_quantity:
                    return error_response(
                        f"Coupon can only be applied on order quantity between the range of {coupon.min_purchase_quantity} and {coupon.max_purchase_quantity}",
                        status_code=status.HTTP_400_BAD_REQUEST
                        )
            elif not coupon.min_purchase_quantity and coupon.min_purchase_quantity < quantity:
                return error_response(
                        f"Coupon can only be applied on order quantity greater than {coupon.min_purchase_quantity}",
                        status_code=status.HTTP_400_BAD_REQUEST
                        )
            elif not coupon.max_purchase_quantity and coupon.max_purchase_quantity > quantity:
                return error_response(
                        f"Coupon can only be applied on order quantity less than {coupon.max_purchase_quantity}",
                        status_code=status.HTTP_400_BAD_REQUEST
                        )
            serializer = CouponBuyerSerializer(coupon)
            return success_response(serializer.data, "Valid Coupon")
        else:
            return error_response(
            "Coupon not valid for selected product",
            status.HTTP_400_BAD_REQUEST
        )


class CouponDetailView(APIView):
    """Get coupon by ID. Admin Only"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, code, *args, **kwargs):
        """Get coupon by the unique coupon code"""
        if not code:
            return error_response("No coupon code provided",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        
        """Retrieve coupon by the unique code and handle exceptions"""
        try:
            coupon = Coupon.objects.get(code=code)
            serializer = CouponSerializer(coupon)
            return success_response(serializer.data,
                                    "Coupon fetched successfully")
        except Coupon.DoesNotExist:
            """Coupon does not exist. Error 404"""
            return error_response("Coupon not found", status.HTTP_404_NOT_FOUND)
        except Exception as e:
            """Catch any unexpected exception"""
            print(f"Error while getting coupon datails: {str(e)}")
            logger.error(f"Internal Server Error while getting coupon details: {e}")
            return error_response("Interner Server Error while fetching coupon",
                                  status.HTTP_500_INTERNAL_SERVER_ERROR)


class CouponListView(APIView):
    """Get a list of all coupon. Admin only"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, *args, **kwargs):
        """Get all coupons"""
        try:
            coupons = Coupon.objects.all().order_by('created_at')
            serializer = CouponSerializer(coupons, many=True)

            return success_response(serializer.data, "Coupons fetched successfully")
        
        except Exception as e:
            """Log exception details"""
            logger.error(f"Internal Server Error while fetching coupon: {str(e)}")
            print(f"Error while fetching coupon: {str(e)}")
            return error_response("Internal Server Error while fetching coupon", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SellerCouponListCreateView(APIView):
    """Create a coupon and get a list of all coupon created by a seller"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Get all coupon created by a seller"""
        try:
            coupons = Coupon.objects.filter(seller=request.user)
            serializer = CouponSerializer(coupons, many=True)
            return success_response(serializer.data, "Coupons fetched successfully")
        except Coupon.DoesNotExist:
            """seller has not created any coupon"""
            return error_response("Seller has not created any coupon", status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Internal Serner Error while getting coupon: {str(e)}")
            print(f"Internal Serner Error while getting coupon: {str(e)}")
            return error_response("Internal Serner Error while getting coupon", status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, *args, **kwargs):
        """Method to create a coupon"""
        try:
            data = request.data
            if not data:
                return error_response("No data provided",
                                      status.HTTP_400_BAD_REQUEST)
            """Ensure that the seller is the logged in user"""
            data['seller'] = request.user
            serializer = CouponSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    data=serializer.data,
                    message="Coupon created successfully.",
                    status_code=status.HTTP_201_CREATED,
                )
            return error_response(
                message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(f"Error creating coupon: {str(e)}")
            logger.error(f"Error creating coupon: {e}")
            return error_response(
                message="Internal Server Error occured while creating the coupon",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SellerCouponDetailUpdateDeleteView(APIView):
    """Seller can view details of a coupon, update and delete it"""
    permission_classes = [IsOwnerSeller]
    
    def get(self, request, code, *args, **kwargs):
        """Get coupon by the unique coupon code"""
        if not code:
            return error_response("No coupon code provided",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        
        """Retrieve coupon by the unique code and handle exceptions"""
        try:
            coupon = Coupon.objects.get(code=code)
            self.check_object_permissions(request, coupon)   # check if user is the owner of the coupon
            serializer = CouponSerializer(coupon)
            return success_response(serializer.data,
                                    "Coupon fetched successfully")
        except Coupon.DoesNotExist:
            """Coupon does not exist. Error 404"""
            return error_response("Coupon not found", status.HTTP_404_NOT_FOUND)
        except PermissionDenied:
            """User is not the owner of the coupon"""
            return error_response("User is not the owner of the coupon", status.HTTP_403_FORBIDDEN)
        except Exception as e:
            """Catch any unexpected exception"""
            print(f"Error while fetching coupon: {str(e)}")
            logger.error(f"Interner Server Error while fetching seller coupon: {e}")
            return error_response("Interner Server Error while fetching seller coupon",
                                  status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, code, *args, **kwargs):
        """Seller update coupon they created"""
        if not code:
            return error_response("No coupon code provided",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        try:
            coupon = Coupon.objects.get(code=code)
            self.check_object_permissions(request, coupon)  # check if user is the owner of the coupon
            data = request.data
            if not data:
                return error_response("No data provided",
                                      status.HTTP_400_BAD_REQUEST)
            """Ensure the seller field cannot be changed"""
            data.pop('seller', None)
            serializer = CouponSerializer(coupon, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    data=serializer.data,
                    message="Coupon updated successfully.",
                )
            return error_response(
                message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Coupon.DoesNotExist:
            return error_response(
                message="Coupon not found", status_code=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied:
            """User is not the owner of the coupon"""
            return error_response("User is not the owner of the coupon", status.HTTP_403_FORBIDDEN)
        except Exception as e:
            print(f"Error while updating coupon: {str(e)}")
            logger.error(f"Internal Server Error updating coupon: {e}")
            return error_response(
                message="Internal Server Error occured while creating the coupon",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        pass

    def delete(self, request, code, *args, **kwargs):
        """Seller delete coupon they created"""
        if not code:
            return error_response("No coupon code provided",
                                  status_code=status.HTTP_400_BAD_REQUEST)
        try:
            coupon = Coupon.objects.get(code=code)
            self.check_object_permissions(request, coupon) # check if user is the owner of the coupon
            coupon.delete()
            return success_response(
                message="Coupon deleted successfully.",
                status_code=status.HTTP_204_NO_CONTENT
                )
        except Coupon.DoesNotExist:
            return error_response("Coupon not found", status_code=status.HTTP_404_NOT_FOUND)
        except PermissionDenied:
            """User is not the owner of the coupon"""
            return error_response("User is not the owner of the coupon", status.HTTP_403_FORBIDDEN)
        except Exception as e:
            print(f"Error while deleting coupon: {str(e)}")
            logger.error(f"Internal Server Error occured while deleting coupon: {e}")
            return error_response(
                message="Internal Server Error occured while deleting coupon",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
