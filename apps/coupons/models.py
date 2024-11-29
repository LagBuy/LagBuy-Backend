from django.db import models
import uuid

class Copon(model.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=50)
    discount_type
    discount_value
    min_purchase_amount
    max_puchase_amount
    valid_from
    valid_to
    usage_limit
    used_count
    applicable_to
    status
    created_at
    updated_at

    class Meta:
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'

    def __str__(self):
        """object return string"""
