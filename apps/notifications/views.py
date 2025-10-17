from rest_framework.views import APIView
from django.utils import timezone
import uuid

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Notification, WebhookEvent
from .serializers import NotificationSerializer
from .utils import create_notification


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user).order_by("-created_at")


class NotificationMarkReadView(generics.UpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def patch(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        serializer = self.get_serializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WebhookReceiverView(APIView):
    """Generic webhook receiver that logs and processes incoming events."""

    authentication_classes = []  # usually unauthenticated
    permission_classes = []

    def post(self, request, *args, **kwargs):
        source = request.headers.get("X-Webhook-Source", "unknown")
        payload = request.data
        event_id = payload.get("event_id") or str(uuid.uuid4())
        
        if not event_id:
            return Response({"error": "Missing event_id"}, status=status.HTTP_400_BAD_REQUEST)
        
        event, created = WebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={
                "source": source,
                "payload": payload,
            },
        )

        if not created:
            return Response(
                {"detail": "Duplicate event"},
                status=status.HTTP_200_OK
            )

        # Process logic (example: successful payment)
        try:
            event.last_attempt_at = timezone.now()
            
            # Require status field
            if "status" not in payload:
                raise ValueError("Missing required field: status")
            
            # Process successful payment
            if payload.get("status") == "success":
                user_email = payload.get("customer_email")
                amount = payload.get("amount")
                
                if not user_email:
                    raise ValueError("Missing customer_email for successful payment")

                # fetch user
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.filter(email=user_email).first()
                if not user:
                    raise Exception(f"No user found for email {user_email}")
              
                create_notification(
                    title="Payment Successful",
                    user=user,
                    message=f"Your payment of ₦{amount} was successful.",
                    notification_type="order",
                )

            event.processed = True
            event.save()
            return Response(
                {"detail": "Webhook processed"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            event.retries += 1
            event.save()
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
