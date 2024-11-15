from rest_framework import permissions, viewsets

from .models import Review
from .serializers import ReviewSerializer


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.buyer == request.user


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)

    def get_queryset(self):
        product_id = self.request.query_params.get("product_id")
        if product_id:
            return self.queryset.filter(product_id=product_id)
        return self.queryset

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return super().get_serializer(*args, **kwargs)
