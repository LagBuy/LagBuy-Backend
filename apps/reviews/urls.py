from django.urls import path
from drf_spectacular.utils import extend_schema_view, extend_schema

from .views import ReviewViewSet

ReviewViewSet = extend_schema_view(
    list=extend_schema(tags=["Reviews"], summary="List Reviews"),
    create=extend_schema(tags=["Reviews"], summary="Create a Review"),
    retrieve=extend_schema(tags=["Reviews"], summary="Retrieve a Review"),
    update=extend_schema(tags=["Reviews"], summary="Update a Review"),
    destroy=extend_schema(tags=["Reviews"], summary="Delete a Review"),
)(ReviewViewSet)

review_list = ReviewViewSet.as_view({"get": "list", "post": "create"})

review_detail = ReviewViewSet.as_view(
    {"get": "retrieve", "put": "update", "delete": "destroy"}
)

urlpatterns = [
    path("", review_list, name="review-list"),
    path("<uuid:pk>/", review_detail, name="review-detail"),
]
