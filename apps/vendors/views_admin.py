import logging
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

from apps.notifications.models import Notification
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.products.models import Product
from apps.profiles.models import VendorsProfile
from apps.vendors.models import AuditLog
from common.utils.responses import error_response, success_response

logger = logging.getLogger(__name__)


class AdminVendorActionView(APIView):
    """
    Admin-only View to approve/suspend vendors and change plans of vendors (basic, premium, enterprise)
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, vendor_id):
        vendor_profile = get_object_or_404(VendorsProfile, id=vendor_id)
        action = request.data.get("action")
        reason = request.data.get("reason", "")
        actor = request.user

        try:
            if action == "approve":
                vendor_profile.is_verified = True
                vendor_profile.save(update_fields=["is_verified"])
                AuditLog.objects.create(
                    user=actor,
                    action="approve_vendor",
                    target=str(vendor_profile.id),
                    details={"reason": reason},
                )
                Notification.objects.create(
                    user=vendor_profile.user,
                    title="Account approved",
                    message="Your vendor account has been approved.",
                    notification_type="subscription",
                )
                return success_response(message="Vendor approved", data="None")

            if action == "suspend":
                vendor_profile.is_suspended = True
                vendor_profile.save(update_fields=["is_suspended"])
                AuditLog.objects.create(
                    user=actor,
                    action="suspend_vendor",
                    target=str(vendor_profile.id),
                    details={"reason": reason},
                )
                Notification.objects.create(
                    user=vendor_profile.user,
                    title="Account suspended",
                    message=f"Your vendor account has been suspended. Reason: {reason}",
                    notification_type="subscription",
                )
                return success_response(message="Vendor suspended", data="None")

            if action == "change_plan":
                plan = request.data.get("plan")
                if plan not in dict(vendor_profile.PLAN_CHOICES):
                    return error_response("Invalid plan", status.HTTP_400_BAD_REQUEST)
                old = vendor_profile.plan_type
                vendor_profile.plan_type = plan
                vendor_profile.save(update_fields=["plan_type"])
                AuditLog.objects.create(
                    user=actor,
                    action="change_plan",
                    target=str(vendor_profile.id),
                    details={"old": old, "new": plan},
                )
                Notification.objects.create(
                    user=vendor_profile.user,
                    title="Plan changed",
                    message=f"Your plan has been changed to {plan}.",
                    notification_type="subscription",
                )
                return success_response(
                    message="Plan Changed Successfully", data="None"
                )

            return error_response("Invalid plan", status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return error_response(message=e.detail, status_code=403)
        except Exception as e:
            logger.error(f"Error while carrying out admin action: {e}")
            return error_response(
                message=f"An error occurred while carrying out action {e}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminStatsView(APIView):
    """
    Returns global stats if admin; otherwise vendor-only stats.
    Stats: total_vendors, total_orders, total_sales, total_products, total_customers (distinct)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            if user.is_staff:
                # global stats
                total_vendors = VendorsProfile.objects.count()
                total_orders = Order.objects.count()
                total_sales = (
                    Payment.objects.filter(payment_status="paid").aggregate(
                        total=Sum("amount")
                    )["total"]
                    or 0
                )
                total_products = Product.objects.count()
                data = {
                    "total_vendors": total_vendors,
                    "total_orders": total_orders,
                    "total_sales": float(total_sales),
                    "total_products": total_products,
                }
                return success_response(message="All Stats returned", data=data)

            # vendor stats - restrict to vendor's data
            if hasattr(user, "vendor_profile"):
                vendor = user
                total_sales = (
                    Payment.objects.filter(
                        order__items__product__seller=vendor, payment_status="paid"
                    ).aggregate(total=Sum("amount"))["total"]
                    or 0
                )
                total_orders = (
                    Order.objects.filter(items__product__seller=vendor)
                    .distinct()
                    .count()
                )
                total_products = vendor.products.count()
                data = {
                    "total_sales": float(total_sales),
                    "total_orders": total_orders,
                    "total_products": total_products,
                }
                return success_response(message="Vendor Stats returned", data=data)

            return error_response("Unauthorized", status.HTTP_403_FORBIDDEN)
        except PermissionDenied as e:
            return error_response(message=e.detail, status_code=403)
        except Exception as e:
            logger.error(f"Error while getting stats: {e}")
            return error_response(
                message=f"An error occurred while getting stats {e}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
