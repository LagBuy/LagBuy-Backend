import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.products.models import Product
from apps.userAuth.models import CustomUser


class Review(models.Model):
    """Model for product reviews."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
        related_query_name="review",
    )
    buyer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="reviews",
        related_query_name="review",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "buyer"], name="unique_review_per_product_per_user"
            )
        ]

    def __str__(self):
        return f"Review of {self.product.name} by {self.buyer.username} - Rating: {self.rating}"
