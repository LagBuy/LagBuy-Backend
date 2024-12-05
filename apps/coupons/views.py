import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .models import Coupon
from .serializers import CouponSerializer
from common.utils.responses import success_response, error_response

logger = logging.getLogger(__name__)


class VerifyCouponView(APIView):
    """Verify the validity of a coupon on a product"""
    # TODO - Check that the coupon has not expired,
    # - it is applied to the valid product,
    # - it meets the order quantity requirements and other requirements
    pass

class CouponDetailView(APIView):
    """Get coupon by ID"""
    permission_classes = [IsAdminUser]
    
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
            return error_response("Interner Server Error while fetching coupon",
                                  status.HTTP_500_INTERNAL_SERVER_ERROR)



class CouponListView(APIView):
    """Get a list of all coupon"""
    permission_class = [IsAdminUser]
    
    def get(self, request, *args, **kwargs):
        """Get all coupons"""
        try:
            coupons = Coupon.objects.all()
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
            coupons = Coupon.objects.get(seller=request.user)
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
        pass
    


class SellerCouponDetailUpdateDeleteView(APIView):
    """Seller can view details of a coupon, update and delete it"""
    permission_classes = [] # TODO - Add permission class to allow only seller to access all their created coupon
    
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
            return error_response("Interner Server Error while fetching coupon",
                                  status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, code, *args, **kwargs):
        """Seller update coupon they created"""
        pass

    def delete():
        """Seller delete coupon they created"""
        pass
