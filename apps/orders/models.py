import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.coupons.models import Coupon
from apps.products.models import Product
from apps.userAuth.models import CustomUser

# TODO: implement is_deleted for some of the models (use a class that handles it all)


class Order(models.Model):
    """
    Represents a customer's order, containing one or more order items.
    Tracks payment and delivery status, and provides total price and delivery fee calculations.
    """

    class PaymentStatus(models.TextChoices):
        """
        Enum for payment status of an order.
        """

        UNPAID = "UNPAID", "Unpaid"
        PAID = "PAID", "Paid"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    buyer = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="orders"
    )
    delivery_address = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def payment_status(self):
        """
        Returns PAID if any related payment has status 'paid', else UNPAID.
        """
        if self.payments.filter(payment_status="paid").exists():
            return self.PaymentStatus.PAID
        return self.PaymentStatus.UNPAID

    @property
    def total_price(self):
        """
        Returns the total price for all items in the order, after discounts.
        """
        return (
            sum([item.total_price for item in self.items.all()]) + self.service_charge
        )

    # TODO: Update this to use a more accurate delivery fee calculation
    @property
    def delivery_fee(self):
        """
        Returns the delivery fee for the order (5% of total price).
        """
        return 0.00  # 0.05 * float(self.total_price)

    # TODO: Update this once it has been discussed
    @property
    def delivery_status(self):
        """
        Returns 'completed' if all items are delivered,
        'pending' if any item is pending or shipped or returned,
        or 'pending' if there are no items.
        """
        statuses = list(self.items.values_list("delivery_status", flat=True))
        if not statuses:
            return "pending"
        if all(s == OrderItem.DeliveryStatus.DELIVERED for s in statuses):
            return "completed"
        return "pending"

    @property
    def service_charge(self):
        """
        Returns the service charge for the order.
        """
        return Decimal(600)  # Flat rate service charge of 600

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order - {self.id} by {self.buyer} [{self.payment_status}]"


class OrderItem(models.Model):
    """
    Represents a single product within an order.
    Can optionally have a coupon applied for discounts.
    """

    class DeliveryStatus(models.TextChoices):
        """
        Enum for delivery status of an order item.
        """

        PENDING = "PENDING", "Pending"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        RETURNED = "RETURNED", "Returned"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    quantity = models.PositiveIntegerField(default=1)
    delivery_status = models.CharField(
        max_length=10, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING
    )
    ready_for_pickup = models.BooleanField(default=False)
    picked_up = models.BooleanField(default=False)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    stock_locked = models.BooleanField(default=False)

    # Relationships
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    rider = models.ForeignKey(
        CustomUser,
        related_name="items",
        null=True,
        on_delete=models.SET_NULL,
        help_text="The rider that accept the Order will be registered here and be responsible for delivering it",
    )
    assigned_riders = models.ManyToManyField(
        CustomUser,
        help_text="Multiple riders can be assigned to an Order item to either accept or decline it",
    )
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def total_price(self) -> Decimal:
        """
        Returns the total price for this order item, factoring in any coupon discount.
        Supports both percent and fixed value discounts.
        Take a snapshot of the purchase price the first time this is called and
        return that value on subsequent calls.
        """
        if self.purchase_price is not None:
            return self.purchase_price
        if self.coupon:
            discount = self.coupon.discount_value
            if self.coupon.discount_type == Coupon.DiscountType.PERCENT:
                discount = (discount / 100) * self.product.price
            self.purchase_price = Decimal(self.product.price) * self.quantity - Decimal(
                discount
            )
            return self.purchase_price
        self.purchase_price = Decimal(self.product.price) * self.quantity
        return self.purchase_price

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
