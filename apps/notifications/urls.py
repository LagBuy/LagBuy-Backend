from django.urls import path
from .views import NotificationListView, NotificationMarkReadView, WebhookReceiverView
from drf_spectacular.utils import extend_schema_view, extend_schema


NotificationListView = extend_schema_view(
    get=extend_schema(tags=["Notifications"], summary="List all notifications"),
)(NotificationListView)

NotificationMarkReadView = extend_schema_view(
    patch=extend_schema(tags=["Notifications"], summary="Mark a notification as read"),
)(NotificationMarkReadView)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notifications-list"),
    path("<uuid:pk>/read/", NotificationMarkReadView.as_view(), name="notification-mark-read"),
    path("webhook/", WebhookReceiverView.as_view(), name="notifications-webhook"),
]
