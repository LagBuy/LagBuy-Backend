from decimal import Decimal
import logging

from django.db import transaction
from django.db.models import Sum

from apps.orders.models import OrderItem
from apps.vendors.models import VendorWallet

logger = logging.getLogger(__name__)


def distribute_payment_to_vendors(order):
    """Compute vendor shares for an order and credit vendor wallets.

    Assumes order is an Order instance with related items accessible via order.items
    Returns a mapping of vendor_id -> credited_amount (Decimal).
    """
    credits = {}
    # aggregate per-product vendor totals
    qs = (
        OrderItem.objects.filter(order=order)
        .values("product__seller")
        .annotate(total_qty_sum=Sum("quantity"))
    )

    # use item-level sums instead: loop items to compute vendor totals reliably
    for item in order.items.select_related("product__seller").all():
        seller = item.product.seller
        seller_id = seller.id
        amt = Decimal(item.quantity) * Decimal(item.product.price)
        credits.setdefault(seller_id, Decimal("0.00"))
        credits[seller_id] += amt

    # Credit each vendor's wallet inside a transaction
    result = {}
    with transaction.atomic():
        for seller_id, amount in credits.items():
            try:
                wallet = VendorWallet.objects.select_for_update().get(
                    vendor_id=seller_id
                )
            except VendorWallet.DoesNotExist:
                # create wallet automatically if missing
                from apps.userAuth.models import CustomUser

                seller = CustomUser.objects.get(id=seller_id)
                wallet = VendorWallet.objects.create(
                    vendor=seller, balance=Decimal("0.00")
                )
            new_balance = wallet.credit(amount)
            result[str(seller_id)] = amount
            logger.info(
                f"Credited {amount} to vendor {seller_id}, new balance {new_balance}"
            )

    return result
