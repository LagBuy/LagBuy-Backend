# contains specific settings for the user authentication
from datetime import timedelta

# SIMPLE_JWT = {
#     "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
# }

REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'jwt-token',
    'JWT_AUTH_REFRESH_COOKIE': 'refresh-token',
    'USER_DETAILS_SERIALIZER': 'apps.users.serializers.CustomUserSerializer',
    'REGISTER_SERIALIZER': 'apps.userauth.serializers.CustomRegisterSerializer',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1)
}

ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
# ACCOUNT_EMAIL_VERIFICATION = 'optional'
# ACCOUNT_CONFIRM_EMAIL_ON_GET = True
# LOGIN_URL = ''

SITE_ID = 1

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
