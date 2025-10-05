import csv
from datetime import timedelta
from io import StringIO
from typing import Dict, List, Tuple

from django.core.exceptions import FieldError
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate, TruncWeek
from django.utils import timezone

from apps.orders.models import OrderItem
from apps.products.models import Product


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
                )[
                    "r"
                ]
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
                )[
                    "r"
                ]
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
