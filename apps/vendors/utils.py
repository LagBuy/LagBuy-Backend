import csv
from datetime import timedelta
from io import BytesIO, StringIO
from typing import Dict, List, Tuple

from django.core.exceptions import FieldError
from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Value,
    Subquery,
    OuterRef,
)
from django.db.models.functions import Coalesce, TruncDate, TruncWeek
from django.utils import timezone
from django.core.files.base import ContentFile

from apps.orders.models import OrderItem, Order
from apps.payments.models import Payment
from apps.products.models import Product

from dateutil.relativedelta import relativedelta

from common.services.storage import STORAGE

from reportlab.pdfgen import canvas


def vendor_aggregates_and_products(
    seller, include_profit: bool = False
) -> Tuple[Dict, List[dict]]:
    """Return totals and per-product metrics for a seller.

    Returns:
        totals: dict with total_qty_all(int), total_revenue_all(float), total_orders(int)
        products_with_metrics: list of dicts {id,name,total_sold,total_revenue,profit}
    """
    paid_q = Q(order__payments__payment_status="paid")
    seller_paid_q = paid_q & Q(product__seller=seller)

    totals = OrderItem.objects.filter(seller_paid_q).aggregate(
        total_qty_all=Coalesce(Sum("quantity"), Value(0)),
        total_revenue_all=Coalesce(
            Sum(
                ExpressionWrapper(
                    F("quantity") * F("product__price"),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            ),
            Value(0, output_field=DecimalField(max_digits=18, decimal_places=2)),
        ),
    )

    total_qty_all = int(totals.get("total_qty_all", 0) or 0)
    total_revenue_all = float(totals.get("total_revenue_all", 0) or 0.0)
    total_orders = (
        OrderItem.objects.filter(seller_paid_q).values("order").distinct().count()
    )

    sold_agg = (
        OrderItem.objects.filter(seller_paid_q)
        .values("product", "product__name", "product__price")
        .annotate(
            total_qty=Coalesce(Sum("quantity"), Value(0)),
            total_revenue=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F("quantity") * F("product__price"),
                        output_field=DecimalField(max_digits=18, decimal_places=2),
                    )
                ),
                Value(0, output_field=DecimalField(max_digits=18, decimal_places=2)),
            ),
        )
    )

    products_with_metrics = []
    total_profit_all = 0.0
    sold_product_ids = set()

    # bulk fetch cost_price only if requested
    cost_map = {}
    if include_profit:
        # Try to bulk fetch cost_price where available. Use values_list to get ids
        # (avoids iterating the queryset twice) and guard the values() call in case
        # the field doesn't exist on this Product model.
        try:
            product_ids = list(sold_agg.values_list("product", flat=True))
            if product_ids:
                for p in Product.objects.filter(id__in=product_ids).values(
                    "id", "price", "cost_price"
                ):
                    cost_map[p["id"]] = p.get("cost_price")
        except FieldError:
            # cost_price doesn't exist on Product; skip profit computation
            cost_map = {}

    for s in sold_agg:
        pid = s.get("product")
        sold_product_ids.add(pid)
        qty = int(s.get("total_qty", 0) or 0)
        revenue = float(s.get("total_revenue", 0) or 0.0)
        profit = None
        if include_profit:
            # support both int and str keyed maps just in case
            cp = cost_map.get(pid) if pid in cost_map else cost_map.get(str(pid))
            if cp is not None:
                profit = (float(s.get("product__price")) - float(cp)) * qty
                total_profit_all += profit
        products_with_metrics.append(
            {
                "id": str(pid),
                "name": s.get("product__name"),
                "total_sold": qty,
                "total_revenue": revenue,
                "profit": profit,
            }
        )

    # include zero-sales products (avoid requesting cost_price if it doesn't exist)
    zero_fields = ["id", "name", "price"]
    if hasattr(Product, "cost_price"):
        zero_fields.append("cost_price")

    zero_qs = (
        Product.objects.filter(seller=seller)
        .exclude(id__in=sold_product_ids)
        .values(*zero_fields)
    )
    for p in zero_qs:
        products_with_metrics.append(
            {
                "id": str(p["id"]),
                "name": p["name"],
                "total_sold": 0,
                "total_revenue": 0.0,
                "profit": None,
            }
        )

    totals_clean = {
        "orders": total_orders,
        "quantity_sold": total_qty_all,
        "revenue": total_revenue_all,
        "profit": float(total_profit_all) if include_profit else None,
    }

    return totals_clean, products_with_metrics


def vendor_trend_data(seller, days: int = 30, trend: str = "daily") -> List[dict]:
    """Return list of trend buckets (daily or weekly) for the seller over days."""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days - 1)

    paid_q = Q(order__payments__payment_status="paid")
    seller_paid_q = paid_q & Q(product__seller=seller)

    trend_data = []
    if trend == "weekly":
        current = start_date
        while current <= end_date:
            week_end = min(current + timedelta(days=6), end_date)
            qty = (
                OrderItem.objects.filter(
                    seller_paid_q,
                    order__created_at__date__gte=current,
                    order__created_at__date__lte=week_end,
                ).aggregate(q=Coalesce(Sum("quantity"), 0))["q"]
                or 0
            )
            revenue = (
                OrderItem.objects.filter(
                    seller_paid_q,
                    order__created_at__date__gte=current,
                    order__created_at__date__lte=week_end,
                ).aggregate(
                    r=Coalesce(
                        Sum(
                            ExpressionWrapper(
                                F("quantity") * F("product__price"),
                                output_field=DecimalField(
                                    max_digits=18, decimal_places=2
                                ),
                            )
                        ),
                        Value(
                            0,
                            output_field=DecimalField(max_digits=18, decimal_places=2),
                        ),
                    )
                )["r"]
                or 0
            )
            trend_data.append(
                {
                    "start": current.isoformat(),
                    "end": week_end.isoformat(),
                    "quantity": int(qty),
                    "revenue": float(revenue),
                }
            )
            current = week_end + timedelta(days=1)
    else:
        for i in range(days - 1, -1, -1):
            d = end_date - timedelta(days=i)
            qty = (
                OrderItem.objects.filter(
                    seller_paid_q, order__created_at__date=d
                ).aggregate(q=Coalesce(Sum("quantity"), 0))["q"]
                or 0
            )
            revenue = (
                OrderItem.objects.filter(
                    seller_paid_q, order__created_at__date=d
                ).aggregate(
                    r=Coalesce(
                        Sum(
                            ExpressionWrapper(
                                F("quantity") * F("product__price"),
                                output_field=DecimalField(
                                    max_digits=18, decimal_places=2
                                ),
                            )
                        ),
                        Value(
                            0,
                            output_field=DecimalField(max_digits=18, decimal_places=2),
                        ),
                    )
                )["r"]
                or 0
            )
            trend_data.append(
                {"date": d.isoformat(), "quantity": int(qty), "revenue": float(revenue)}
            )

    return trend_data


def build_lost_customers_csv(users, last_map):
    """Return CSV bytes for given users and last_purchase mapping.

    Args:
        users: iterable of CustomUser objects (with optional user_profile relation)
        last_map: dict mapping user id -> last_p urchase datetime

    Returns:
        bytes: UTF-8 encoded CSV bytes
    """
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["id", "email", "first_name", "last_name", "last_purchase"])
    for u in users:
        lp = last_map.get(str(u.id)) or last_map.get(u.id)
        writer.writerow(
            [
                str(u.id),
                u.email,
                getattr(getattr(u, "user_profile", None), "first_name", ""),
                getattr(getattr(u, "user_profile", None), "last_name", ""),
                lp.isoformat() if lp is not None else "",
            ]
        )
    return csv_buffer.getvalue().encode("utf-8")


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


def _payments_queryset_for_vendor(vendor_user, params):
    """
    Return Payment queryset filtered by params (start_date/end_date/etc).
    """
    qs = Payment.objects.filter(order__items__product__seller=vendor_user)
    start = params.get("start_date")
    end = params.get("end_date")
    if start:
        qs = qs.filter(created_at__gte=start)
    if end:
        qs = qs.filter(created_at__lte=end)
    return qs.order_by("created_at")


def generate_csv_bytes_for_payments(payments_qs):
    """Return bytes of CSV file for Payment queryset"""
    output = StringIO()
    writer = csv.writer(output)
    # header
    writer.writerow(
        [
            "payment_ref",
            "order_id",
            "amount",
            "currency",
            "status",
            "created_at",
            "buyer_email",
        ]
    )
    for p in payments_qs:
        writer.writerow(
            [
                getattr(p, "ref", ""),
                getattr(p.order, "id", ""),
                str(p.amount),
                getattr(p, "currency", ""),
                getattr(p, "payment_status", ""),
                p.created_at.isoformat() if getattr(p, "created_at", None) else "",
                p.user.email if getattr(p, "user", None) else "",
            ]
        )
    data = output.getvalue().encode("utf-8")
    output.close()
    return data


def generate_pdf_bytes_for_payments(payments_qs):
    """Return bytes (PDF) for Payment queryset."""
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    y = 800
    p.setFont("Helvetica", 12)
    p.drawString(50, y, "Vendor Transactions Report")
    y -= 30
    for pay in payments_qs:
        line = f"Ref: {getattr(pay, 'ref', '')} | Order: {getattr(pay.order, 'id', '')} | Amount: {pay.amount} | Status: {pay.payment_status} | Date: {pay.created_at}"
        p.drawString(50, y, line[:120])  # simple truncation
        y -= 15
        if y < 50:
            p.showPage()
            y = 800
    p.save()
    buffer.seek(0)
    return buffer.read()


def upload_bytes_to_storage(bytes_data: bytes, filename: str, export_format: str):
    """
    Upload bytes to storage and return url.
    """

    try:
        if export_format == "csv":
            STORAGE.s3_client.put_object(
                Bucket=STORAGE.bucket_name,
                Key=filename,
                Body=bytes_data,
                ContentType="text/csv",
            )
            url = STORAGE.get_file_url(filename)
            return url
        elif export_format == "pdf":
            STORAGE.s3_client.put_object(
                Bucket=STORAGE.bucket_name,
                Key=filename,
                Body=bytes_data,
                ContentType="text/pdf",
            )
            url = STORAGE.get_file_url(filename)
            return url
        else:
            raise ValueError("unsupported export format")

    except Exception as e:
        print(e, "error")
        raise Exception("Error uploading to storage")


def create_export_file_for_vendor(
    vendor_user, export_format, params, payments_limit=None
):
    """
    Generate file bytes and upload to storage, return (path url).
    If payments_limit is provided, payments_qs can be sliced for sampling.
    """
    payments_qs = _payments_queryset_for_vendor(vendor_user, params)
    if payments_limit:
        payments_qs = payments_qs[:payments_limit]
    if export_format == "csv":
        data_bytes = generate_csv_bytes_for_payments(payments_qs)
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        filename = f"exports/{vendor_user.email.replace('@', '_')}_transactions_{timestamp}.csv"
        url = upload_bytes_to_storage(data_bytes, filename, "csv")
        return filename, url

    elif export_format == "pdf":
        data_bytes = generate_pdf_bytes_for_payments(payments_qs)
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        filename = f"exports/{vendor_user.email.replace('@', '_')}_transactions_{timestamp}.pdf"
        url = upload_bytes_to_storage(data_bytes, filename, "pdf")
        return filename, url

    else:
        raise ValueError("unsupported export format")
