import uuid

from django.db import models
from django.utils import timezone

from apps.coupons.models import Coupon
from apps.userAuth.models import CustomUser


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
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    name = models.CharField(max_length=225)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    verified = models.BooleanField(default=False)
    stock_quantity = models.PositiveIntegerField()
    locked_quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    seller = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="products"
    )
    categories = models.ManyToManyField(Category, related_name="products")
    coupons = models.ManyToManyField(Coupon, related_name="products", blank=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} by {self.seller}"

    @property
    def available_stock(self):
        """Return the available stock after reserved/locked quantity."""
        return max(0, self.stock_quantity - (self.locked_quantity or 0))


class ProductImage(models.Model):
    """
    Model representing an image of a product.
    Each product can have multiple images.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image_url = models.URLField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Image for {self.product.name}"
