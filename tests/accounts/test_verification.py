from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import EmailVerificationToken
from accounts.services import (
    register_user,
    resend_verification_email,
    verify_email,
)
from common.exceptions import ApplicationError

User = get_user_model()


@pytest.mark.django_db
def test_verify_email_success():
    user, raw_token = register_user(
        email="verify_me@example.com",
        username="verify_user",
        password="Password123!",
    )
    assert user.email_verified_at is None

    verified_user = verify_email(raw_token)
    assert verified_user.id == user.id
    assert verified_user.email_verified_at is not None
    assert verified_user.is_email_verified is True

    # Token record updated
    token_record = EmailVerificationToken.objects.get(user=user)
    assert token_record.used_at is not None


@pytest.mark.django_db
def test_verify_email_single_use():
    user, raw_token = register_user(
        email="single_use@example.com",
        username="single_user",
        password="Password123!",
    )
    verify_email(raw_token)

    # Second verification attempt fails
    with pytest.raises(ApplicationError) as exc_info:
        verify_email(raw_token)
    assert exc_info.value.code == "invalid_verification_token"


@pytest.mark.django_db
def test_verify_email_expired_token():
    user, raw_token = register_user(
        email="expired_token@example.com",
        username="expired_user",
        password="Password123!",
    )
    now = timezone.now()
    # Fast forward token expiration into the past while respecting expires_at > created_at
    EmailVerificationToken.objects.filter(user=user).update(
        created_at=now - timedelta(hours=48),
        expires_at=now - timedelta(hours=24),
    )

    with pytest.raises(ApplicationError) as exc_info:
        verify_email(raw_token)
    assert exc_info.value.code == "invalid_verification_token"


@pytest.mark.django_db
def test_resend_verification_invalidates_earlier_tokens():
    user, first_token = register_user(
        email="resend_user@example.com",
        username="resend_user",
        password="Password123!",
    )

    first_record = EmailVerificationToken.objects.get(user=user)
    assert first_record.used_at is None

    # Resend token
    second_token = resend_verification_email("resend_user@example.com")
    assert second_token is not None
    assert second_token != first_token

    first_record.refresh_from_db()
    assert first_record.used_at is not None  # invalidated

    # Attempting to use the first token now fails
    with pytest.raises(ApplicationError):
        verify_email(first_token)

    # Using the second token succeeds
    verified_user = verify_email(second_token)
    assert verified_user.is_email_verified is True


@pytest.mark.django_db
def test_verify_and_resend_api_endpoints():
    client = APIClient()
    user, raw_token = register_user(
        email="api_verify@example.com",
        username="api_verify_user",
        password="Password123!",
    )

    # Verify via API
    resp = client.post("/api/v1/auth/verify-email/", data={"token": raw_token})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["message"] == "Email address verified successfully."

    # Resend via API for already verified user returns generic 200 without creating new tokens
    count_before = EmailVerificationToken.objects.filter(user=user).count()
    resend_resp = client.post(
        "/api/v1/auth/resend-verification/",
        data={"email": "api_verify@example.com"},
    )
    assert resend_resp.status_code == status.HTTP_200_OK
    count_after = EmailVerificationToken.objects.filter(user=user).count()
    assert count_before == count_after
