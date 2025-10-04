from django.urls import path
from .views import NotificationListView, NotificationMarkReadView
from drf_spectacular.utils import extend_schema_view, extend_schema


NotificationListView = extend_schema_view(
    get=extend_schema(tags=["Notifications"], summary="List all notifications"),
)(NotificationListView)

NotificationMarkReadView = extend_schema_view(
    patch=extend_schema(tags=["Notifications"], summary="Mark a notification as read"),
)(NotificationMarkReadView)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notifications-list"),
    path("<int:pk>/read/", NotificationMarkReadView.as_view(), name="notification-mark-read"),
]
