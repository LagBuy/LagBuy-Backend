from apps.notifications.models import Notification
import logging

logger = logging.getLogger(__name__)


def create_notification(user, message, notification_type, title=None):
    """Helper to create a notification safely"""
    try:
        if title is None:
            title = message[:255]
            
        Notification.objects.create(
            user=user,
            message=message,
            notification_type=notification_type,
            title=title
        )
        logger.info(f"[Notification] Created notification for user {user.email}: {message}")
    except Exception as e:
        logger.error(f"[Notification Error] Failed to create notification: {e}")
        raise 
        # use logging instead of raising errors
