"""
Integration tests for rate throttling across auth, write, and public read endpoints.
Verifies rate enforcement, 429 status, Retry-After header, error envelope,
and public read exemption.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from blog.models import Category

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": (
            "rest_framework_simplejwt.authentication.JWTAuthentication",
        ),
        "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticatedOrReadOnly",),
        "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPageNumberPagination",
        "PAGE_SIZE": 10,
        "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
        "DEFAULT_THROTTLE_CLASSES": ("common.throttles.WriteRateThrottle",),
        "DEFAULT_THROTTLE_RATES": {
            "auth": "2/minute",
            "write": "3/minute",
        },
    }
)
def test_auth_rate_throttle_enforcement_and_envelope():
    client = APIClient()

    # Rate is 2/min. First 2 requests succeed or fail with 400/401 (not 429)
    res1 = client.post("/api/v1/auth/login/", {"email": "test1@example.com", "password": "wrong"})
    assert res1.status_code == status.HTTP_401_UNAUTHORIZED

    res2 = client.post("/api/v1/auth/login/", {"email": "test2@example.com", "password": "wrong"})
    assert res2.status_code == status.HTTP_401_UNAUTHORIZED

    # 3rd request within the same minute is throttled
    res3 = client.post("/api/v1/auth/login/", {"email": "test3@example.com", "password": "wrong"})
    assert res3.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    # Check Retry-After header
    assert "Retry-After" in res3.headers
    assert int(res3.headers["Retry-After"]) > 0

    # Check error envelope
    assert "error" in res3.data
    assert res3.data["error"]["code"] == "throttled"
    assert "Request was throttled" in res3.data["error"]["message"]
    assert "wait_seconds" in res3.data["error"]["details"]
    assert res3.data["error"]["details"]["wait_seconds"] is not None
    assert "request_id" in res3.data


@pytest.mark.django_db
@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": (
            "rest_framework_simplejwt.authentication.JWTAuthentication",
        ),
        "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticatedOrReadOnly",),
        "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPageNumberPagination",
        "PAGE_SIZE": 10,
        "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
        "DEFAULT_THROTTLE_CLASSES": ("common.throttles.WriteRateThrottle",),
        "DEFAULT_THROTTLE_RATES": {
            "auth": "100/minute",
            "write": "2/minute",
        },
    }
)
def test_public_reads_never_throttled():
    client = APIClient()
    Category.objects.create(name="Tech", slug="tech")

    # Issue 10 successive GET requests (well above write limit of 2/min)
    for _ in range(10):
        res = client.get("/api/v1/categories/")
        assert res.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": (
            "rest_framework_simplejwt.authentication.JWTAuthentication",
        ),
        "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticatedOrReadOnly",),
        "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPageNumberPagination",
        "PAGE_SIZE": 10,
        "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
        "DEFAULT_THROTTLE_CLASSES": ("common.throttles.WriteRateThrottle",),
        "DEFAULT_THROTTLE_RATES": {
            "auth": "100/minute",
            "write": "2/minute",
        },
    }
)
def test_write_rate_throttle_enforcement_for_authenticated_user():
    client = APIClient()
    user = User.objects.create_user(
        email="throttled_writer@example.com",
        username="writer_throttle",
        password="Password123!",
    )
    from django.utils import timezone

    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at"])

    client.force_authenticate(user=user)
    cat = Category.objects.create(name="Python", slug="python")

    # 1st write
    res1 = client.post(
        "/api/v1/posts/",
        {"title": "Post 1", "category_slug": cat.slug, "content_markdown": "Body 1"},
    )
    assert res1.status_code == status.HTTP_201_CREATED

    # 2nd write
    res2 = client.post(
        "/api/v1/posts/",
        {"title": "Post 2", "category_slug": cat.slug, "content_markdown": "Body 2"},
    )
    assert res2.status_code == status.HTTP_201_CREATED

    # 3rd write exceeds limit of 2/minute -> throttled
    res3 = client.post(
        "/api/v1/posts/",
        {"title": "Post 3", "category_slug": cat.slug, "content_markdown": "Body 3"},
    )
    assert res3.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert res3.data["error"]["code"] == "throttled"
    assert "Retry-After" in res3.headers
