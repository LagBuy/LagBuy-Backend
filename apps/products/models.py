from django.db import models
from django.utils import timezone
import uuid

# import apps.users.models

from apps.users.models import CustomUser

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=225)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    images = models.JSONField()
    verified = models.BooleanField(default=False)
    stock_quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    """Relationships for products model"""
    seller = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='products')
    # carts = models.ManyToManyField('Cart', related_name='products')
    # categories = models.ManyToManyField('Category', related_name='products')
    # orders = models.ManyToManyField('Order', through='OrderProduct', related_name='products')
    # reviews = models.ForeignKey('Review', on_delete=models.CASCADE, related_name='product_reviews', null=True,
    #                             blank=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['-created_at']  # Optional: orders by newest products first

    def __str__(self):
        return f'{self.name} by {self.seller}'

