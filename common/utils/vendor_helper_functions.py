# vendors/services/analytics_service.py
from django.db.models import Sum, F, Count, Q, Subquery, OuterRef
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from apps.orders.models import Order, OrderItem
from apps.products.models import Product, Category


def get_vendor_analytics(seller_user):
    """
    Returns a dict of analytics values for the given seller (CustomUser).
    This intentionally mirrors the logic used by the separate endpoints so tests remain consistent.
    """
    seller = seller_user

    # --- Total products ---
    total_products = seller.products.count()

    # --- Total sales (sum of order item prices for paid orders for this seller) ---
    paid_items_qs = OrderItem.objects.filter(
        order__payments__payment_status="paid", product__seller=seller
    ).distinct()

    total_sales_agg = paid_items_qs.aggregate(
        total_sales=Sum(F("quantity") * F("product__price"))
    )
    total_sales = float(total_sales_agg["total_sales"] or 0)

    # --- Total orders (distinct orders that include this seller's paid items) ---
    total_orders = (
        Order.objects.filter(
            items__product__seller=seller, payments__payment_status="paid"
        )
        .distinct()
        .count()
    )

    # --- Average Order Value (AOV) ---
    average_order_value = round(total_sales / total_orders, 2) if total_orders else 0.0

    # --- Total unique customers (ever) who bought from this seller (paid) ---
    total_customers = (
        Order.objects.filter(
            items__product__seller=seller, payments__payment_status="paid"
        )
        .values("buyer")
        .distinct()
        .count()
    )

    # --- New customers in last N days (defaults to 30) - reuse logic from NewCustomers view ---
    days = 30
    days_ago = timezone.now() - timedelta(days=days)
    first_orders_subquery = (
        OrderItem.objects.filter(
            product__seller=seller, order__buyer=OuterRef("order__buyer")
        )
        .order_by("order__created_at")
        .values("order__created_at")[:1]
    )
    new_customers_qs = (
        OrderItem.objects.filter(
            product__seller=seller, order__payments__payment_status="paid"
        )
        .annotate(first_order_date=Subquery(first_orders_subquery))
        .filter(first_order_date__gte=days_ago)
        .values(
            "order__buyer__user_profile__first_name",
            "order__buyer__user_profile__last_name",
        )
        .distinct()
        .annotate(
            first_name=F("order__buyer__user_profile__first_name"),
            last_name=F("order__buyer__user_profile__last_name"),
        )
        .values("first_name", "last_name")
    )
    new_customers_count = new_customers_qs.count()
    new_customers = list(new_customers_qs)

    # --- Sales per month for last 12 months (re-use SalesPerMonth's approach) ---
    start_date = timezone.now() - relativedelta(years=1)
    start_date = start_date.replace(day=1)
    end_date = timezone.now()
    order_items_for_months = paid_items_qs.filter(order__created_at__gte=start_date)
    current_date = start_date
    sales_per_month = {}
    while current_date <= end_date:
        next_month = current_date + relativedelta(months=1)
        key = current_date.strftime("%m-%Y")
        monthly_items = order_items_for_months.filter(
            order__created_at__gte=current_date,
            order__created_at__lt=next_month,
        )
        monthly_total = (
            monthly_items.aggregate(total=Sum(F("quantity") * F("product__price")))[
                "total"
            ]
            or 0
        )
        sales_per_month[key] = float(monthly_total)
        current_date = next_month

    # --- Sales growth: compare last 30 days vs previous 30 days ---
    now = timezone.now()
    current_period_start = now - timedelta(days=30)
    previous_period_start = now - timedelta(days=60)

    current_sales = (
        paid_items_qs.filter(order__created_at__gte=current_period_start).aggregate(
            total=Sum(F("quantity") * F("product__price"))
        )["total"]
        or 0
    )

    previous_sales = (
        paid_items_qs.filter(
            order__created_at__range=[previous_period_start, current_period_start]
        ).aggregate(total=Sum(F("quantity") * F("product__price")))["total"]
        or 0
    )

    sales_growth_percentage = 0.0
    if previous_sales > 0:
        sales_growth_percentage = round(
            ((current_sales - previous_sales) / previous_sales) * 100, 2
        )

    # --- Low stock (default <5) - reuse LowStock logic but return count and list ---
    low_stock_qs = seller.products.filter(stock_quantity__lt=5).values(
        "name", "stock_quantity"
    )
    low_stock_count = low_stock_qs.count()
    low_stock_products = list(low_stock_qs)

    # --- Category distribution (reuse existing logic but return percentages) ---
    products = seller.products.all().prefetch_related("categories")
    cats = []
    for p in products:
        cats += list(p.categories.all())
    cat_names = [c.name for c in cats]
    total = len(cat_names) or 1
    categories_counts = {}
    for name in set(cat_names):
        categories_counts[name] = cat_names.count(name)
    category_distribution = {k: (v / total) * 100 for k, v in categories_counts.items()}

    # --- Revenue by category (sum money per product category for paid items) ---
    revenue_by_category_qs = paid_items_qs.values("product__categories__name").annotate(
        total_revenue=Sum(F("quantity") * F("product__price"))
    )
    revenue_by_category = {}
    for item in revenue_by_category_qs:
        name = item.get("product__categories__name") or "Uncategorized"
        revenue_by_category[name] = float(item.get("total_revenue") or 0)

    # --- Conversion rate: not available without visitor tracking. So let's set None or 0. ---
    # it should be conversion_rate = round((total_orders / visitor_count) * 100, 2) if visitor_count else 0
    conversion_rate = 0

    return {
        "total_sales": float(total_sales),
        "total_products": total_products,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "average_order_value": float(average_order_value),
        "new_customers_count": new_customers_count,
        "new_customers": new_customers,
        "sales_per_month": sales_per_month,
        "sales_growth_percentage": sales_growth_percentage,
        "low_stock_count": low_stock_count,
        "low_stock_products": low_stock_products,
        "category_distribution": category_distribution,
        "revenue_by_category": revenue_by_category,
        "conversion_rate": conversion_rate,
    }
