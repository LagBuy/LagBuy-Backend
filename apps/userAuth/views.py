from rest_framework import generics, permissions
from .models import CustomUser
from .serializers import CustomUserSerializer

class UserList(generics.ListAPIView):
    """Users get view class"""
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

class UserDetail(generics.RetrieveAPIView):
    """User detail view class"""
    lookup_field = 'username'
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

class LoggedUser(generics.RetrieveAPIView):
    """User profile get view class"""
    serializer_class = CustomUserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        """object to be used"""
        return self.request.user

# TODO: create a view to see individual users detail (vendor and admin only)
# TODO: create a view to see all users (admin only)
