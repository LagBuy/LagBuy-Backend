import os
from pathlib import Path

from environs import Env

from apps.userAuth.settings import *

env = Env()
env.read_env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env.str("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)

APPEND_SLASH = True  #
MEDIA_URL = "/media/"  #
MEDIA_ROOT = os.path.join(BASE_DIR, "media")  #

ALLOWED_HOSTS = [".amazonaws.com", ".lagbuy.com", "172.31.46.206", "13.244.200.121", ".elasticbeanstalk.com", "localhost", "127.0.0.1"]

AUTH_USER_MODEL = "userAuth.CustomUser"

# Admin email configuration
ADMINS = [
    ("Admin", env.str("ADMIN_EMAIL", default="chinwezechisom@gmail.com")),
    ("LagBuy Team", "lagbuy008@gmail.com"),
]
SITE_NAME = env.str("SITE_NAME", default="LagBuy")
SERVER_EMAIL = env.str("SERVER_EMAIL", default="no-reply@lagbuy.com")
SUPPORT_EMAIL = env.str("SUPPORT_EMAIL", default="support@lagbuy.com")
LOGIN_URL = env.str("LOGIN_URL", default="shop.lagbuy.com/login")

# Email configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend" # "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = "smtp.hostinger.com"
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[LagBuy Team] "

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # 3rd-party apps
    "rest_framework",
    "corsheaders",
    "rest_framework_simplejwt",
    "rest_framework.authtoken",
    "dj_rest_auth",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "dj_rest_auth.registration",
    "drf_spectacular",
    "django_filters",
    # local
    "apps.userAuth",
    "apps.products",
    "apps.orders",
    "apps.cart",
    "apps.reviews",
    "apps.coupons",
    "apps.riders",
    "apps.vendors",
    "apps.profiles",
    "apps.payments",
    "apps.notifications",
    "common",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",  #
]

AUTHENTICATION_BACKENDS = [
    "allauth.account.auth_backends.AuthenticationBackend",  #
    "django.contrib.auth.backends.ModelBackend",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "dj_rest_auth.jwt_auth.JWTCookieAuthentication",  #
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DJANGO_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ],
    "EXCEPTION_HANDLER": "common.utils.custom_exception_handler.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "LagBuy Backend Project",
    "DESCRIPTION": "Here is the documentation for the backend project",
    "VERSION": "1.0.0",
}

# CORS / CSRF: allow only the production LagBuy domains
CORS_ALLOWED_ORIGINS = [
    "https://lagbuy.com",
    "https://shop.lagbuy.com",
    "https://vendors.lagbuy.com",
    "https://riders.lagbuy.com",
]

CSRF_TRUSTED_ORIGINS = [
    "https://lagbuy.com",
    "https://shop.lagbuy.com",
    "https://vendors.lagbuy.com",
    "https://riders.lagbuy.com",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

ROOT_URLCONF = "lagbuy.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",  #
            ],
        },
    },
]

WSGI_APPLICATION = "lagbuy.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

if "RDS_DB_NAME" in os.environ:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": os.environ["RDS_DB_NAME"],
            "USER": os.environ["RDS_USERNAME"],
            "PASSWORD": os.environ["RDS_PASSWORD"],
            "HOST": os.environ["RDS_HOSTNAME"],
            "PORT": os.environ["RDS_PORT"],
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# AWS S3 Configuration
AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID", default=None)
AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY", default=None)
AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME", default=None)
AWS_S3_REGION_NAME = env.str("AWS_S3_REGION_NAME", default=None)

# Paystack Configuration
PAYSTACK_BASE_URL = "https://api.paystack.co"
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_TEST_SECRET_KEY")
IP_WHITELIST = ["52.31.139.75", "52.49.173.169", "52.214.14.220"]

# Automatic payout thresholds (wallet-driven daily payouts)
# Minimum wallet balance eligible for an automatic payout (default: 1000.00 NGN)
DAILY_PAYOUT_MIN = env.float("DAILY_PAYOUT_MIN", default=5000.00)
# Maximum amount to payout in a single automatic payout (default: 100000.00 NGN)
DAILY_PAYOUT_MAX = env.float("DAILY_PAYOUT_MAX", default=100000.00)

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "GMT"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging configuration
# LOGGING = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "formatters": {
#         "verbose": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
#         "simple": {"format": "%(levelname)s %(message)s"},
#     },
#     "handlers": {
#         "file": {
#             "level": "DEBUG",
#             "class": "logging.FileHandler",
#             "filename": os.path.join(BASE_DIR, "debug.log"),
#             "formatter": "verbose",
#         },
#     },
#     "root": {
#         "handlers": ["file"],
#         "level": "DEBUG",
#     },
#     "loggers": {
#         "django": {
#             "handlers": ["file"],
#             "level": "INFO",
#             "propagate": True,
#         },
#     },
# }
