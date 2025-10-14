from apps.notifications.models import Notification
# import logging


def create_notification(user, message, notification_type):
    """Helper to create a notification safely"""
    try:
        Notification.objects.create(
            user=user,
            message=message,
            notification_type=notification_type
        )
    except Exception as e:
        print(f"[Notification Error] Failed to create notification: {e}")
        # logger.error(f"[Notification Error] Failed to create notification: {e}") 
        # use logging instead of raising errors
