from rest_framework import generics
from .models import CustomUser
from .serializers import CustomUserSerializer

class UserList(generics.ListAPIView): # get request
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

class UserDetail(generics.RetrieveAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
