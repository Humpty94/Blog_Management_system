import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.views import APIView

from accounts.permissions import IsEmailVerified
from common.exceptions import EmailNotVerifiedError

User = get_user_model()


def test_is_email_verified_permission_anonymous():
    factory = RequestFactory()
    request = factory.get("/")
    from django.contrib.auth.models import AnonymousUser

    request.user = AnonymousUser()

    permission = IsEmailVerified()
    view = APIView()

    assert permission.has_permission(request, view) is False


def test_is_email_verified_permission_unverified_user():
    factory = RequestFactory()
    request = factory.get("/")
    user = User(id=1, email="unverified@example.com", username="unverified", is_active=True)
    request.user = user

    permission = IsEmailVerified()
    view = APIView()

    with pytest.raises(EmailNotVerifiedError):
        permission.has_permission(request, view)


def test_is_email_verified_permission_verified_user():
    factory = RequestFactory()
    request = factory.get("/")
    user = User(
        id=2,
        email="verified@example.com",
        username="verified",
        is_active=True,
        email_verified_at=timezone.now(),
    )
    request.user = user

    permission = IsEmailVerified()
    view = APIView()

    assert permission.has_permission(request, view) is True
