import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.products.models import Product
from apps.users.models import CustomUser


class Order(models.Model):
    """Model representing an order."""

    class PaymentStatus(models.TextChoices):
        """Payment status choices for an order."""

        UNPAID = "UNPAID", "Unpaid"
        PAID = "PAID", "Paid"

    class DeliveryStatus(models.TextChoices):
        """Delivery status choices for an order."""

        PENDING = "PENDING", "Pending"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        RETURNED = "RETURNED", "Returned"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    buyer = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="orders"
    )
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    delivery_address = models.TextField()
    delivery_status = models.CharField(
        max_length=10, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_price(self):
        """Calculate the total price of the order."""
        return sum([item.total_price for item in self.items.all()])

    @property
    def delivery_fee(self):
        """Calculate the delivery fee for the order."""
        return 0.05 * float(self.total_price)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order - {self.id} by {self.buyer}"

# TODO: Edit the coupon field to a FK field
# TODO: calculate the total_price with consideration of the coupon discount
class OrderItem(models.Model):
    """Model representing an item in an order."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    coupon = models.CharField(max_length=50, blank=True, null=True)

    @property
    def total_price(self):
        """Calculate the total price for this order item."""
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
