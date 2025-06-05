from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import APIStatusView

urlpatterns = [
    path('', APIStatusView.as_view(), name='api-status'),
    path("admin/", admin.site.urls),
    path("api/v1/profile/", include("apps.users.urls"), name="user_profile"),
    path("api/v1/auth/", include("apps.users.urls"), name="user_authentication"),
    path("api/v1/products/", include("apps.products.urls")),
    path("api/v1/orders/", include("apps.orders.urls"), name="orders"),
    path("api/v1/coupon/", include("apps.coupons.urls"), name="coupon"),
    path("api/v1/cart/", include("apps.cart.urls"), name="cart"),
    path("api/v1/reviews/", include("apps.reviews.urls"), name="reviews"),
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
