import uuid

from django.db import models
from django.utils import timezone

from apps.users.models import CustomUser


class Category(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

# TODO: Implement adding multiple images to a product
class Product(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    name = models.CharField(max_length=225)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    images = models.JSONField()
    verified = models.BooleanField(default=False)
    stock_quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    seller = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="products"
    )
    categories = models.ManyToManyField(Category, related_name="products")

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} by {self.seller}"
