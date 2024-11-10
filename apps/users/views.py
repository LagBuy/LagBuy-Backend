from rest_framework import generics, permissions
from .models import CustomUser
from .serializers import CustomUserSerializer

class UserList(generics.ListAPIView): # get request
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

class UserDetail(generics.RetrieveAPIView):
    lookup_field = 'username'
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

class LoggedUser(generics.RetrieveAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user
