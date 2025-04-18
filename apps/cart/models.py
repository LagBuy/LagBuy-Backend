from django.db import models

from apps.products.models import Product
from apps.users.models import CustomUser

# TODO: Remove the user field from the CartItem model
class CartItem(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.quantity} of {self.product.name} in {self.user.username}'s cart"

    @property
    def total_price(self):
        return self.quantity * self.product.price

# TODO: use a OneToMany field for the Cart model
class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    items = models.ManyToManyField(CartItem)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s cart"

    @property
    def total_price(self):
        return sum([item.total_price for item in self.items.all()])
