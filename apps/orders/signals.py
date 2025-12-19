from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.orders.models import Order
from apps.notifications.utils import create_notification


@receiver(post_save, sender=Order)
def order_created_notification(sender, instance, created, **kwargs):
    """Notify buyer when order is placed."""
    if created:
        create_notification(
            user=instance.buyer,
            message=f"Your order #{instance.id} has been placed successfully.",
            notification_type="order",
            title="Order Placed Successfully",
        )
