from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from accounts.urls import auth_urlpatterns, users_urlpatterns

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", include("common.urls")),
    path("api/v1/auth/", include((auth_urlpatterns, "auth"))),
    path("api/v1/users/", include((users_urlpatterns, "users"))),
]

# OpenAPI documentation in dev mode
if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            "api/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
    ]
