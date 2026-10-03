from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from accounts.urls import auth_urlpatterns, users_urlpatterns
from blog.urls import (
    blog_users_urlpatterns,
    categories_urlpatterns,
    posts_urlpatterns,
)
from comments.urls import (
    comments_urlpatterns,
    post_comments_urlpatterns,
)
from engagement.urls import (
    engagement_users_urlpatterns,
    post_engagement_urlpatterns,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", include("common.urls")),
    path("api/v1/auth/", include((auth_urlpatterns, "auth"))),
    path("api/v1/categories/", include((categories_urlpatterns, "categories"))),
    path("api/v1/posts/", include((post_engagement_urlpatterns, "post-engagement"))),
    path("api/v1/posts/", include((post_comments_urlpatterns, "post-comments"))),
    path("api/v1/posts/", include((posts_urlpatterns, "posts"))),
    path("api/v1/comments/", include((comments_urlpatterns, "comments"))),
    path("api/v1/users/", include((engagement_users_urlpatterns, "engagement-users"))),
    path("api/v1/users/", include((blog_users_urlpatterns, "blog-users"))),
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
