"""
Utility functions for sending email notifications
"""
import logging
from decimal import Decimal
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)


def send_vendor_new_order_email(order, vendor):
    """
    Send an email to a vendor notifying them of a new paid order.
    
    Args:
        order: Order instance
        vendor: CustomUser instance (the vendor)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Get vendor's items from the order
        vendor_items = order.items.filter(product__seller=vendor).select_related('product')
        
        if not vendor_items.exists():
            logger.warning(f"No items found for vendor {vendor.email} in order {order.id}")
            return False
        
        # Calculate subtotal for vendor's items only
        vendor_subtotal = sum(item.total_price for item in vendor_items)
        
        # Prepare order items data for template
        order_items_data = []
        for item in vendor_items:
            order_items_data.append({
                'product_name': item.product.name,
                'quantity': item.quantity,
                'unit_price': f"{item.product.price:,.2f}",
                'subtotal': f"{item.total_price:,.2f}",
            })
        
        # Get vendor name
        vendor_profile = getattr(vendor, 'user_profile', None)
        if vendor_profile:
            vendor_name = vendor_profile.first_name or vendor.email.split('@')[0]
        else:
            vendor_name = vendor.email.split('@')[0]
        
        # Get customer name
        customer_profile = getattr(order.buyer, 'user_profile', None)
        if customer_profile:
            customer_name = f"{customer_profile.first_name} {customer_profile.last_name}".strip()
            if not customer_name:
                customer_name = order.buyer.email.split('@')[0]
        else:
            customer_name = order.buyer.email.split('@')[0]
        
        # Get vendor dashboard URL from settings
        vendor_dashboard_url = getattr(settings, 'VENDOR_URL', 'https://vendors.lagbuy.com/')
        if not vendor_dashboard_url.endswith('/'):
            vendor_dashboard_url += '/'
        vendor_dashboard_url += f"orders/{order.id}/"
        
        # Prepare context for the email template
        context = {
            'vendor_name': vendor_name,
            'site_name': getattr(settings, 'SITE_NAME', 'LagBuy'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@lagbuy.com'),
            'order_id': str(order.id)[:8],  # Short version of UUID for readability
            'order_date': order.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'customer_name': customer_name,
            'order_items': order_items_data,
            'subtotal': f"{vendor_subtotal:,.2f}",
            'total_amount': f"{vendor_subtotal + order.service_charge:,.2f}",
            'vendor_dashboard_url': vendor_dashboard_url,
        }
        
        # Render email subject
        subject = render_to_string('emails/vendor_new_order_subject.txt', context)
        subject = "".join(subject.splitlines())  # Remove any newlines
        
        # Render HTML email template
        html_message = render_to_string('emails/vendor_new_order.html', context)
        
        # Render plain text email template
        try:
            plain_message = render_to_string('emails/vendor_new_order.txt', context)
        except Exception as e:
            # If text template fails, use stripped HTML as fallback
            logger.warning(f"Failed to render text template, using HTML fallback: {e}")
            plain_message = strip_tags(html_message)
        
        # Get vendor email
        vendor_email = vendor.email
        
        # Create email with both HTML and plain text versions
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[vendor_email]
        )
        email.attach_alternative(html_message, "text/html")
        
        # Send the email
        email.send(fail_silently=False)
        
        logger.info(f"Vendor new order email sent successfully to {vendor_email} for order {order.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send vendor new order email for order {order.id}: {str(e)}", exc_info=True)
        return False


def notify_vendor_of_new_order(order):
    """
    Send email notification to the vendor of a new paid order.
    
    Note: An order can only contain items from a single vendor.
    
    Args:
        order: Order instance
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Get the vendor from the first order item (all items belong to same vendor)
        first_item = order.items.select_related('product__seller').first()
        
        if not first_item:
            logger.warning(f"No items found in order {order.id}")
            return False
        
        vendor = first_item.product.seller
        success = send_vendor_new_order_email(order, vendor)
        
        if success:
            logger.info(f"Notified vendor {vendor.email} for order {order.id}")
        else:
            logger.warning(f"Failed to notify vendor {vendor.email} for order {order.id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error notifying vendor for order {order.id}: {str(e)}", exc_info=True)
        return False


def send_admin_new_order_email(order):
    """
    Send an email to admins notifying them of a new paid order that needs delivery coordination.
    
    Args:
        order: Order instance
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Get admin emails from settings
        admin_emails = getattr(settings, 'SEND_NEW_ORDER_DETAILS', [])
        
        if not admin_emails:
            logger.warning("SEND_NEW_ORDER_DETAILS not configured in settings")
            return False
        
        if not isinstance(admin_emails, list):
            admin_emails = [admin_emails]
        
        # Get order items
        order_items = order.items.select_related('product', 'product__seller', 'product__seller__user_profile').all()
        
        if not order_items.exists():
            logger.warning(f"No items found in order {order.id}")
            return False
        
        # Get vendor info from first item (all items belong to same vendor)
        first_item = order_items.first()
        vendor = first_item.product.seller
        
        # Get vendor user profile for name
        user_profile = getattr(vendor, 'user_profile', None)
        if user_profile:
            vendor_name = f"{user_profile.first_name} {user_profile.last_name}".strip()
            if not vendor_name:
                vendor_name = vendor.email.split('@')[0]
            vendor_phone = user_profile.phone_number or 'N/A'
        else:
            vendor_name = vendor.email.split('@')[0]
            vendor_phone = 'N/A'
        
        # Get vendor business profile for business info
        vendor_profile = getattr(vendor, 'vendor_profile', None)
        if vendor_profile:
            vendor_business_name = vendor_profile.business_name or 'N/A'
            business_address = vendor_profile.business_address or ''
            business_city = vendor_profile.business_location_city or ''
            business_state = vendor_profile.business_location_state or ''
            
            address_parts = [business_address, business_city, business_state]
            vendor_address = ', '.join(filter(None, address_parts))
            if not vendor_address:
                vendor_address = 'Address not available'
        else:
            vendor_business_name = 'N/A'
            vendor_address = 'Address not available'
        
        # Get customer info
        customer_profile = getattr(order.buyer, 'user_profile', None)
        if customer_profile:
            customer_name = f"{customer_profile.first_name} {customer_profile.last_name}".strip()
            if not customer_name:
                customer_name = order.buyer.email.split('@')[0]
            customer_phone = customer_profile.phone_number or 'N/A'
        else:
            customer_name = order.buyer.email.split('@')[0]
            customer_phone = 'N/A'
        
        # Get delivery address from order
        delivery_address = getattr(order, 'delivery_address', 'Address not available')
        
        # Prepare order items data for template
        order_items_data = []
        items_names = []
        for item in order_items:
            order_items_data.append({
                'product_name': item.product.name,
                'quantity': item.quantity,
                'unit_price': f"{item.product.price:,.2f}",
                'subtotal': f"{item.total_price:,.2f}",
            })
            items_names.append(item.product.name)
        
        # Calculate totals
        subtotal = sum(item.total_price for item in order_items)
        
        # Get rider pay from settings or use default
        rider_pay = getattr(settings, 'DEFAULT_RIDER_PAY', '')
        if isinstance(rider_pay, (int, float, Decimal)):
            rider_pay = f"{rider_pay:,.0f}"
        
        # Prepare context for the email template
        context = {
            'site_name': getattr(settings, 'SITE_NAME', 'LagBuy'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@lagbuy.com'),
            'order_id': str(order.id)[:8],  # Short version of UUID for readability
            'order_id_short': str(order.id)[:8],  # Explicitly for the delivery box
            'order_date': order.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'customer_name': customer_name,
            'customer_email': order.buyer.email,
            'customer_phone': customer_phone,
            'vendor_name': vendor_name,
            'vendor_business_name': vendor_business_name,
            'vendor_email': vendor.email,
            'vendor_phone': vendor_phone,
            'vendor_address': vendor_address,
            'delivery_address': delivery_address,
            'order_items': order_items_data,
            'items_list': ', '.join(items_names),
            'rider_pay': rider_pay,
            'subtotal': f"{subtotal:,.2f}",
            'service_charge': f"{order.service_charge:,.2f}",
            'total_amount': f"{order.total_price:,.2f}",
        }
        
        # Render email subject
        subject = render_to_string('emails/admin_new_order_subject.txt', context)
        subject = "".join(subject.splitlines())  # Remove any newlines
        
        # Render HTML email template
        html_message = render_to_string('emails/admin_new_order.html', context)
        
        # Render plain text email template
        try:
            plain_message = render_to_string('emails/admin_new_order.txt', context)
        except Exception as e:
            # If text template fails, use stripped HTML as fallback
            logger.warning(f"Failed to render text template, using HTML fallback: {e}")
            plain_message = strip_tags(html_message)
        
        # Create email with both HTML and plain text versions
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_emails
        )
        email.attach_alternative(html_message, "text/html")
        
        # Send the email
        email.send(fail_silently=False)
        
        logger.info(f"Admin new order email sent successfully to {admin_emails} for order {order.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send admin new order email for order {order.id}: {str(e)}", exc_info=True)
        return False


def notify_admins_of_new_order(order):
    """
    Send email notification to admins about a new paid order.
    
    Args:
        order: Order instance
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        success = send_admin_new_order_email(order)
        
        if success:
            logger.info(f"Notified admins for order {order.id}")
        else:
            logger.warning(f"Failed to notify admins for order {order.id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error notifying admins for order {order.id}: {str(e)}", exc_info=True)
        return False
