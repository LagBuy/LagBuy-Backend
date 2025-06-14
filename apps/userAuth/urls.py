from django.urls import path, include, re_path

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from dj_rest_auth.registration.views import RegisterView, VerifyEmailView
from dj_rest_auth.views import LoginView, LogoutView, UserDetailsView, PasswordResetConfirmView

urlpatterns = [
    path('', include('dj_rest_auth.urls')),
    path('signup/', include('dj_rest_auth.registration.urls')),
]


# from .views import UserList, UserDetail, LoggedUser

# urlpatterns = [
#     path('me/', LoggedUser.as_view(), name='user_profile'),
#     path('<str:username>/', UserDetail.as_view(), name='user_detail'),
#     path('', UserList.as_view(), name='user_list'),
# ]

