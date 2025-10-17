from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=[
            ("order", "Order"),
            ("withdrawal", "Withdrawal"),
            ("subscription", "Subscription"),
            ("password_change", "Password Change"),
            ("export_job", "Export Job"),
        ]
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.email} - {self.notification_type}"


class WebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(max_length=255, unique=True)
    source = models.CharField(max_length=50)  # e.g. 'paystack', 'flutterwave'
    payload = models.JSONField()  # raw webhook data
    processed = models.BooleanField(default=False)
    retries = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.source} - {self.event_id}"
