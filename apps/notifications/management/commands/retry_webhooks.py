from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.notifications.models import WebhookEvent


class Command(BaseCommand):
    help = "Retry unprocessed webhook events safely"

    def handle(self, *args, **options):
        unprocessed = WebhookEvent.objects.filter(processed=False, retries__lt=3)
        for event in unprocessed:
            # call same logic as WebhookReceiverView.post()
            self.stdout.write(f"Retrying webhook {event.event_id} ({event.retries + 1}/3)")
            event.retries += 1
            event.last_attempt_at = timezone.now()
            event.save()
