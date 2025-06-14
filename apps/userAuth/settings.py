'''contains specific settings for the user authentication'''
import os
from datetime import timedelta
from environs import Env

env = Env()
env.read_env()

REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'jwt-token',
    'JWT_AUTH_REFRESH_COOKIE': 'refresh-token',
    'USER_DETAILS_SERIALIZER': 'apps.userAuth.serializers.CustomUserSerializer',
    'REGISTER_SERIALIZER': 'apps.userAuth.serializers.CustomRegisterSerializer',

    # 'PASSWORD_RESET_SERIALIZER': 'apps.users.serializers.CustomPasswordResetSerializer',
    'PASSWORD_RESET_USE_SITES_DOMAIN': True,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1)
}

ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True

ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None  # Tell allauth there's no username

FRONTEND_URL = 'https://shop.lagbuy.com/'

ACCOUNT_ADAPTER = 'core.adapters.CustomAccountAdapter'
ACCOUNT_EMAIL_VERIFICATION = 'optional'

SITE_ID = 1

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# EMAIL_USE_TLS = True
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
# EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]
# EMAIL_PORT = 587


# ACCOUNT_CONFIRM_EMAIL_ON_GET = True
# LOGIN_URL = ''
