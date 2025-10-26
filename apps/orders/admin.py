from django.contrib import admin
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from django.utils.html import format_html
from django.contrib import messages
from datetime import timedelta
from decimal import Decimal
import uuid

from .models import Order, OrderItem


class PaymentStatusFilter(admin.SimpleListFilter):
    """Custom filter for payment status"""
    title = 'payment status'
    parameter_name = 'payment_status'

    def lookups(self, request, model_admin):
        """Return a list of tuples for the filter options"""
        return [
            ('paid', 'Paid'),
            ('unpaid', 'Unpaid'),
        ]

    def queryset(self, request, queryset):
        """Filter the queryset based on the selected payment status"""
        if self.value() == 'paid':
            # Orders with at least one paid payment
            return queryset.filter(payments__payment_status='paid').distinct()
        elif self.value() == 'unpaid':
            # Orders with no paid payments
            return queryset.exclude(payments__payment_status='paid')
        return queryset


class DeliveryStatusFilter(admin.SimpleListFilter):
    """Custom filter for delivery status"""
    title = 'delivery status'
    parameter_name = 'delivery_status'

    def lookups(self, request, model_admin):
        """Return a list of tuples for the filter options"""
        return [
            ('completed', 'Completed'),
            ('pending', 'Pending'),
        ]

    def queryset(self, request, queryset):
        """Filter the queryset based on delivery status"""
        if self.value() == 'completed':
            # Orders where all items are delivered
            order_ids = []
            for order in queryset:
                if order.delivery_status == 'completed':
                    order_ids.append(order.id)
            return queryset.filter(id__in=order_ids)
        elif self.value() == 'pending':
            # Orders with pending delivery
            order_ids = []
            for order in queryset:
                if order.delivery_status == 'pending':
                    order_ids.append(order.id)
            return queryset.filter(id__in=order_ids)
        return queryset


class OrderItemInline(admin.TabularInline):
    """Inline display for order items"""
    model = OrderItem
    extra = 0
    readonly_fields = ('total_price', 'purchase_price')
    fields = ('product', 'quantity', 'delivery_status', 'coupon', 'total_price', 'ready_for_pickup', 'picked_up', 'rider')
    can_delete = False


class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_id',
        'buyer_info',
        'item_count',
        'subtotal_display',
        'total_price_display',
        'payment_status_badge',
        'delivery_status_badge',
        'created_at',
    )
    list_filter = (PaymentStatusFilter, DeliveryStatusFilter, 'created_at')
    search_fields = ('id', 'buyer__email', 'buyer__user_profile__first_name', 'buyer__user_profile__last_name', 'delivery_address')
    ordering = ['-created_at']
    readonly_fields = ('id', 'created_at', 'updated_at', 'subtotal', 'service_charge', 'total_price', 'delivery_fee', 'payment_status', 'delivery_status')
    inlines = [OrderItemInline]
    actions = ['mark_as_paid']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('id', 'buyer', 'delivery_address', 'created_at', 'updated_at')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'service_charge', 'total_price', 'delivery_fee')
        }),
        ('Status', {
            'fields': ('payment_status', 'delivery_status')
        }),
    )

    def order_id(self, obj):
        """Display shortened order ID"""
        return str(obj.id)[:8] + "..."
    order_id.short_description = 'Order ID'

    def buyer_info(self, obj):
        """Display buyer's name or email"""
        buyer = obj.buyer
        if hasattr(buyer, 'user_profile') and buyer.user_profile.first_name:
            return f"{buyer.user_profile.first_name} {buyer.user_profile.last_name}"
        return buyer.email
    buyer_info.short_description = 'Buyer'

    def item_count(self, obj):
        """Display number of items in order"""
        return obj.items.count()
    item_count.short_description = 'Items'

    def subtotal_display(self, obj):
        """Display subtotal"""
        return f"₦{obj.subtotal:,.2f}"
    subtotal_display.short_description = 'Subtotal'

    def total_price_display(self, obj):
        """Display total price"""
        return f"₦{obj.total_price:,.2f}"
    total_price_display.short_description = 'Total'

    def payment_status_badge(self, obj):
        """Display payment status with color badge"""
        status = obj.payment_status
        if status == Order.PaymentStatus.PAID:
            color = '#28a745'
            icon = '✓'
        else:
            color = '#dc3545'
            icon = '✗'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{} {}</span>',
            color, icon, status.label
        )
    payment_status_badge.short_description = 'Payment'

    def delivery_status_badge(self, obj):
        """Display delivery status with color badge"""
        status = obj.delivery_status
        if status == 'completed':
            color = '#17a2b8'
            icon = '✓'
            label = 'Completed'
        else:
            color = '#ffc107'
            icon = '⏳'
            label = 'Pending'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{} {}</span>',
            color, icon, label
        )
    delivery_status_badge.short_description = 'Delivery'

    def mark_as_paid(self, request, queryset):
        """Admin action to mark selected orders as paid by creating a payment record"""
        from apps.payments.models import Payment, PaymentStatus
        
        paid_count = 0
        already_paid_count = 0
        
        for order in queryset:
            # Check if order is already paid
            if order.payment_status == Order.PaymentStatus.PAID:
                already_paid_count += 1
                continue
            
            try:
                # Create a payment record for this order
                payment = Payment.objects.create(
                    amount=order.total_price,
                    ref=f"ADMIN-{order.id}-{uuid.uuid4().hex[:8]}",
                    verified=True,
                    payment_status=PaymentStatus.PAID,
                    currency='NGN',
                    user=order.buyer,
                    order=order
                )
                
                # Send email notifications to vendor and admins
                try:
                    from common.utils.email_utils import notify_vendor_of_new_order, notify_admins_of_new_order
                    notify_vendor_of_new_order(order)
                    notify_admins_of_new_order(order)
                except Exception as e:
                    # Log the error but don't fail the action
                    self.message_user(
                        request,
                        f"Order {str(order.id)[:8]}... marked as paid but email notification failed: {str(e)}",
                        level=messages.WARNING
                    )
                
                paid_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error marking order {order.id} as paid: {str(e)}",
                    level=messages.ERROR
                )
        
        # Display success/info messages
        if paid_count > 0:
            self.message_user(
                request,
                f"Successfully marked {paid_count} order(s) as paid and sent email notifications.",
                level=messages.SUCCESS
            )
        
        if already_paid_count > 0:
            self.message_user(
                request,
                f"{already_paid_count} order(s) were already paid.",
                level=messages.INFO
            )
    
    mark_as_paid.short_description = "Mark selected orders as paid"

    def changelist_view(self, request, extra_context=None):
        """Override changelist view to add order statistics"""
        extra_context = extra_context or {}
        
        # Get current date/time
        today = timezone.now().date()
        seven_days_ago = timezone.now() - timedelta(days=7)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Get all orders
        all_orders = Order.objects.all()
        
        # Total orders
        total_orders = all_orders.count()
        
        # Orders by payment status
        paid_orders = sum(1 for order in all_orders if order.payment_status == Order.PaymentStatus.PAID)
        unpaid_orders = total_orders - paid_orders
        
        # Orders by delivery status
        completed_deliveries = sum(1 for order in all_orders if order.delivery_status == 'completed')
        pending_deliveries = total_orders - completed_deliveries
        
        # New orders today
        new_orders_today = all_orders.filter(created_at__date=today).count()
        
        # Orders in last 7 days
        orders_last_7_days = all_orders.filter(created_at__gte=seven_days_ago).count()
        
        # Orders in last 30 days
        orders_last_30_days = all_orders.filter(created_at__gte=thirty_days_ago).count()
        
        # Daily stats for last 7 days
        daily_stats = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            count = all_orders.filter(created_at__date=date).count()
            # Calculate revenue for the day
            day_orders = all_orders.filter(created_at__date=date)
            day_revenue = sum(float(order.total_price) for order in day_orders)
            
            daily_stats.append({
                'date': date.strftime('%Y-%m-%d'),
                'day': date.strftime('%A'),
                'count': count,
                'revenue': day_revenue
            })
        
        # Revenue statistics
        total_revenue = sum(float(order.total_price) for order in all_orders if order.payment_status == Order.PaymentStatus.PAID)
        revenue_today = sum(float(order.total_price) for order in all_orders.filter(created_at__date=today) if order.payment_status == Order.PaymentStatus.PAID)
        revenue_last_7_days = sum(float(order.total_price) for order in all_orders.filter(created_at__gte=seven_days_ago) if order.payment_status == Order.PaymentStatus.PAID)
        revenue_last_30_days = sum(float(order.total_price) for order in all_orders.filter(created_at__gte=thirty_days_ago) if order.payment_status == Order.PaymentStatus.PAID)
        
        # Pending revenue (unpaid orders)
        pending_revenue = sum(float(order.total_price) for order in all_orders if order.payment_status == Order.PaymentStatus.UNPAID)
        
        # Total items sold
        total_items = OrderItem.objects.filter(order__in=all_orders).aggregate(
            total_quantity=Sum('quantity')
        )['total_quantity'] or 0
        
        # Items by delivery status
        items_pending = OrderItem.objects.filter(
            delivery_status=OrderItem.DeliveryStatus.PENDING
        ).count()
        items_shipped = OrderItem.objects.filter(
            delivery_status=OrderItem.DeliveryStatus.SHIPPED
        ).count()
        items_delivered = OrderItem.objects.filter(
            delivery_status=OrderItem.DeliveryStatus.DELIVERED
        ).count()
        items_returned = OrderItem.objects.filter(
            delivery_status=OrderItem.DeliveryStatus.RETURNED
        ).count()
        
        # Top buyers
        from django.db.models import Count as DjangoCount
        top_buyers = all_orders.values(
            'buyer__email', 'buyer__id'
        ).annotate(
            order_count=DjangoCount('id')
        ).order_by('-order_count')[:5]
        
        buyer_stats = []
        for buyer in top_buyers:
            buyer_email = buyer['buyer__email']
            # Try to get a better name for the buyer
            from apps.userAuth.models import CustomUser
            try:
                user = CustomUser.objects.get(id=buyer['buyer__id'])
                if hasattr(user, 'user_profile') and user.user_profile.first_name:
                    buyer_name = f"{user.user_profile.first_name} {user.user_profile.last_name}"
                else:
                    buyer_name = buyer_email
            except:
                buyer_name = buyer_email
            
            # Calculate total spent by this buyer
            buyer_orders = all_orders.filter(buyer__id=buyer['buyer__id'])
            total_spent = sum(float(order.total_price) for order in buyer_orders if order.payment_status == Order.PaymentStatus.PAID)
            
            buyer_stats.append({
                'name': buyer_name,
                'order_count': buyer['order_count'],
                'total_spent': total_spent
            })
        
        # Orders requiring attention (unpaid or pending delivery)
        orders_need_attention = sum(1 for order in all_orders if order.payment_status == Order.PaymentStatus.UNPAID or order.delivery_status == 'pending')
        
        # Items ready for pickup
        items_ready_for_pickup = OrderItem.objects.filter(ready_for_pickup=True, picked_up=False).count()
        
        extra_context['total_orders'] = total_orders
        extra_context['paid_orders'] = paid_orders
        extra_context['unpaid_orders'] = unpaid_orders
        extra_context['completed_deliveries'] = completed_deliveries
        extra_context['pending_deliveries'] = pending_deliveries
        extra_context['new_orders_today'] = new_orders_today
        extra_context['orders_last_7_days'] = orders_last_7_days
        extra_context['orders_last_30_days'] = orders_last_30_days
        extra_context['daily_stats'] = daily_stats
        extra_context['total_revenue'] = round(total_revenue, 2)
        extra_context['revenue_today'] = round(revenue_today, 2)
        extra_context['revenue_last_7_days'] = round(revenue_last_7_days, 2)
        extra_context['revenue_last_30_days'] = round(revenue_last_30_days, 2)
        extra_context['pending_revenue'] = round(pending_revenue, 2)
        extra_context['total_items'] = total_items
        extra_context['items_pending'] = items_pending
        extra_context['items_shipped'] = items_shipped
        extra_context['items_delivered'] = items_delivered
        extra_context['items_returned'] = items_returned
        extra_context['buyer_stats'] = buyer_stats
        extra_context['orders_need_attention'] = orders_need_attention
        extra_context['items_ready_for_pickup'] = items_ready_for_pickup
        
        return super().changelist_view(request, extra_context=extra_context)


class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'item_id',
        'order_link',
        'product',
        'quantity',
        'total_price_display',
        'delivery_status_badge',
        'rider_info',
        'ready_for_pickup',
        'picked_up',
    )
    list_filter = ('delivery_status', 'ready_for_pickup', 'picked_up', 'stock_locked')
    search_fields = ('id', 'order__id', 'product__name', 'order__buyer__email')
    ordering = ['-order__created_at']
    readonly_fields = ('id', 'total_price', 'purchase_price')
    
    fieldsets = (
        ('Item Information', {
            'fields': ('id', 'order', 'product', 'quantity', 'purchase_price', 'total_price', 'coupon')
        }),
        ('Delivery Status', {
            'fields': ('delivery_status', 'ready_for_pickup', 'picked_up', 'stock_locked')
        }),
        ('Rider Assignment', {
            'fields': ('rider', 'assigned_riders')
        }),
    )

    def item_id(self, obj):
        """Display shortened item ID"""
        return str(obj.id)[:8] + "..."
    item_id.short_description = 'Item ID'

    def order_link(self, obj):
        """Display link to order"""
        return format_html(
            '<a href="/admin/orders/order/{}/change/">{}</a>',
            obj.order.id,
            str(obj.order.id)[:8] + "..."
        )
    order_link.short_description = 'Order'

    def total_price_display(self, obj):
        """Display total price"""
        return f"₦{obj.total_price:,.2f}"
    total_price_display.short_description = 'Total Price'

    def delivery_status_badge(self, obj):
        """Display delivery status with color badge"""
        status = obj.delivery_status
        colors = {
            'PENDING': '#ffc107',
            'SHIPPED': '#17a2b8',
            'DELIVERED': '#28a745',
            'RETURNED': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(status, '#6c757d'), status
        )
    delivery_status_badge.short_description = 'Status'

    def rider_info(self, obj):
        """Display assigned rider"""
        if obj.rider:
            if hasattr(obj.rider, 'rider_profile'):
                return f"Rider: {obj.rider.email}"
            return obj.rider.email
        return "Not assigned"
    rider_info.short_description = 'Rider'


admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
