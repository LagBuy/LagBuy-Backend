import os
from pathlib import Path

from environs import Env

from apps.userauth.settings import *

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

frontendUrl = "https://shop.lagbuy.com"
ridersUrl = "https://riders.lagbuy.com"

ALLOWED_HOSTS = [frontendUrl, ridersUrl, "*", "0.0.0.0", ".elasticbeanstalk.com", "localhost", "127.0.0.1"]

AUTH_USER_MODEL = "users.CustomUser"

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
    "apps.users",
    "apps.userauth",
    "apps.products",
    "apps.orders",
    "apps.cart",
    "apps.reviews",
    "apps.coupons",
    "apps.riders",
    "common",
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

CORS_ORIGIN_WHITELIST = (
    frontendUrl,
    ridersUrl,
    "http://localhost:5174",
    "http://localhost:5173",
    "http://0.0.0.0:5174",
    "http://0.0.0.0:5173",
    "http://0.0.0.0:3000",
    "http://0.0.0.0:8000",  # TODO: Set this to the frontend URL
)

CSRF_TRUSTED_ORIGINS = [frontendUrl, ridersUrl, "http://localhost:5174", "http://localhost:5173", "http://0.0.0.0:5174", "http://0.0.0.0:5173", "http://0.0.0.0:3000"]  # TODO: Set this to the frontend URL

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = ["accept",
                      "accept-encoding",
                      "authorization",
                      "content-type",
                      "dnt",
                      "origin",
                      "user-agent",
                      "x-csrftoken",
                      "x-requested-with"]
CSRF_TRUSTED_ORIGINS = [
    frontendUrl,
    ridersUrl,
    "http://0.0.0.0:5174",
    "http://0.0.0.0:5173",
    "http://0.0.0.0:3000",
]  # TODO: Set this to the frontend URL

ROOT_URLCONF = "lagbuy.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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
