from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import APIStatusView
from dj_rest_auth.views import PasswordResetView, PasswordResetConfirmView

urlpatterns = [
    path("", APIStatusView.as_view(), name="api-status"),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.userAuth.urls"), name="user_authentication"),
    path("api/v1/products/", include("apps.products.urls")),
    path("api/v1/orders/", include("apps.orders.urls"), name="orders"),
    path("api/v1/payments/", include("apps.payments.urls"), name="payments"),
    path("api/v1/coupon/", include("apps.coupons.urls"), name="coupon"),
    path("api/v1/cart/", include("apps.cart.urls"), name="cart"),
    path("api/v1/reviews/", include("apps.reviews.urls"), name="reviews"),
    path("api/v1/vendors/", include("apps.vendors.urls"), name="analytic"),
    path("api/v1/riders/", include("apps.riders.urls"), name="riders"),
    path("api/v1/profiles/", include("apps.profiles.urls"), name="profiles"),

    # password reset
    path(
        "password/reset/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    # schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
