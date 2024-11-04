from django.urls import path

from .views import UserList, UserDetail, LoggedUser

urlpatterns = [
    path('me/', LoggedUser.as_view(), name='user_profile'),
    path('<str:username>/', UserDetail.as_view(), name='user_detail'),
    path('', UserList.as_view(), name='user_list'),
]

