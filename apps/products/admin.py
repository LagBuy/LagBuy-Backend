from django.contrib import admin
from django.db.models import Count, Q, Avg, Sum
from django.utils import timezone
from datetime import timedelta

from .models import Category, Product, ProductImage


class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "seller",
        "price",
        "stock_quantity",
        "verified",
        "created_at",
        "updated_at",
    )
    list_filter = ("verified", "created_at")
    search_fields = ("name", "description", "seller__email")
    ordering = ["-created_at"]

    def changelist_view(self, request, extra_context=None):
        """Override changelist view to add product statistics"""
        extra_context = extra_context or {}
        
        # Get current date/time
        today = timezone.now().date()
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        # Get total products (excluding soft-deleted)
        total_products = Product.objects.filter(deleted_at__isnull=True).count()
        
        # Get soft-deleted products statistics
        soft_deleted_products = Product.objects.filter(deleted_at__isnull=False).count()
        
        # Get soft-deleted products today
        soft_deleted_today = Product.objects.filter(
            deleted_at__isnull=False, deleted_at__date=today
        ).count()
        
        # Get soft-deleted products in the last 7 days
        soft_deleted_last_7_days = Product.objects.filter(
            deleted_at__isnull=False, deleted_at__gte=seven_days_ago
        ).count()
        
        # Get verified vs unverified products
        verified_products = Product.objects.filter(
            deleted_at__isnull=True, verified=True
        ).count()
        unverified_products = Product.objects.filter(
            deleted_at__isnull=True, verified=False
        ).count()
        
        # Get products with zero stock
        out_of_stock_products = Product.objects.filter(
            deleted_at__isnull=True, stock_quantity=0
        ).count()
        
        # Get products with low stock (1-10 items)
        low_stock_products = Product.objects.filter(
            deleted_at__isnull=True, stock_quantity__gt=0, stock_quantity__lte=10
        ).count()
        
        # Get new products today
        new_products_today = Product.objects.filter(
            deleted_at__isnull=True, created_at__date=today
        ).count()
        
        # Get new products in the last 7 days (daily breakdown)
        daily_stats = []
        for i in range(6, -1, -1):  # Last 7 days including today
            date = today - timedelta(days=i)
            count = Product.objects.filter(
                deleted_at__isnull=True, created_at__date=date
            ).count()
            daily_stats.append({
                'date': date.strftime('%Y-%m-%d'),
                'day': date.strftime('%A'),
                'count': count
            })
        
        # Get products by category
        category_stats = []
        categories = Category.objects.annotate(
            product_count=Count('products', filter=Q(products__deleted_at__isnull=True))
        ).order_by('-product_count')[:10]  # Top 10 categories
        
        for category in categories:
            if category.product_count > 0:
                category_stats.append({
                    'name': category.name,
                    'count': category.product_count
                })
        
        # Get products with no category
        no_category_count = Product.objects.filter(
            deleted_at__isnull=True, categories__isnull=True
        ).count()
        if no_category_count > 0:
            category_stats.append({
                'name': 'No Category',
                'count': no_category_count
            })
        
        # Calculate average price
        avg_price = Product.objects.filter(
            deleted_at__isnull=True
        ).aggregate(Avg('price'))['price__avg'] or 0
        
        # Calculate total inventory value
        products_with_values = Product.objects.filter(
            deleted_at__isnull=True
        ).values_list('price', 'stock_quantity')
        total_inventory_value = sum(
            float(price) * quantity for price, quantity in products_with_values
        )
        
        # Get top sellers (users with most products)
        top_sellers = Product.objects.filter(
            deleted_at__isnull=True
        ).values(
            'seller__email', 'seller__id'
        ).annotate(
            product_count=Count('id')
        ).order_by('-product_count')[:5]
        
        seller_stats = []
        for seller in top_sellers:
            seller_email = seller['seller__email']
            # Try to get a better name for the seller
            from apps.userAuth.models import CustomUser
            try:
                user = CustomUser.objects.get(id=seller['seller__id'])
                if hasattr(user, 'vendor_profile') and user.vendor_profile.business_name:
                    seller_name = user.vendor_profile.business_name
                elif hasattr(user, 'user_profile') and user.user_profile.first_name:
                    seller_name = f"{user.user_profile.first_name} {user.user_profile.last_name}"
                else:
                    seller_name = seller_email
            except:
                seller_name = seller_email
                
            seller_stats.append({
                'name': seller_name,
                'count': seller['product_count']
            })
        
        extra_context['total_products'] = total_products
        extra_context['verified_products'] = verified_products
        extra_context['unverified_products'] = unverified_products
        extra_context['out_of_stock_products'] = out_of_stock_products
        extra_context['low_stock_products'] = low_stock_products
        extra_context['new_products_today'] = new_products_today
        extra_context['daily_stats'] = daily_stats
        extra_context['category_stats'] = category_stats
        extra_context['avg_price'] = round(avg_price, 2)
        extra_context['total_inventory_value'] = round(total_inventory_value, 2)
        extra_context['seller_stats'] = seller_stats
        extra_context['soft_deleted_products'] = soft_deleted_products
        extra_context['soft_deleted_today'] = soft_deleted_today
        extra_context['soft_deleted_last_7_days'] = soft_deleted_last_7_days
        
        return super().changelist_view(request, extra_context=extra_context)


admin.site.register(Product, ProductAdmin)
admin.site.register(Category)
admin.site.register(ProductImage)
