from django.contrib import admin

from .models import Category, Product, ProductImage


class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "seller",
        "price",
        "stock_quantity",
        "verified",
        "created_at",
        "updated_at",
    )
    list_filter = ("verified", "created_at")
    search_fields = ("name", "description", "seller__email")
    ordering = ["-created_at"]


admin.site.register(Product)
admin.site.register(Category)
admin.site.register(ProductImage)
