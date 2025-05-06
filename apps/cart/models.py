from django.db import models

from apps.products.models import Product
from apps.users.models import CustomUser


class Cart(models.Model):
    """
    Represents a shopping cart belonging to a single user.
    Each user has one cart, and each cart can have multiple items.
    """

    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.username}'s cart"

    @property
    def total_price(self):
        """
        Returns the total price of all items in the cart.
        """
        return sum([item.total_price for item in self.items.all()])


class CartItem(models.Model):
    """
    Represents an item in a user's cart.
    Each CartItem is linked to a Cart and a Product.
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        unique_together = ("cart", "product")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.quantity} of {self.product.name} in {self.cart.user.username}'s cart"

    @property
    def total_price(self):
        """
        Returns the total price for this cart item (quantity * product price).
        """
        return self.quantity * self.product.price
