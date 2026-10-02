import hashlib

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import EmailVerificationToken, Profile
from accounts.services import register_user
from common.exceptions import ConflictError

User = get_user_model()


@pytest.mark.django_db
def test_register_user_creates_user_and_profile_atomically():
    user, raw_token = register_user(
        email="NewAuthor@Example.Com",
        username="new_author",
        password="SecurePassword123!",
        display_name="New Author",
        bio="Hello world",
    )

    assert user.email == "newauthor@example.com"
    assert user.username == "new_author"
    assert user.is_active is True
    assert user.email_verified_at is None
    assert user.check_password("SecurePassword123!")

    # Verify Profile was created explicitly
    profile = Profile.objects.get(user=user)
    assert profile.display_name == "New Author"
    assert profile.bio == "Hello world"
    assert profile.effective_display_name == "New Author"

    # Verify EmailVerificationToken exists and raw_token matches hash
    expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token_record = EmailVerificationToken.objects.get(user=user)
    assert token_record.token_hash == expected_hash
    assert token_record.used_at is None


@pytest.mark.django_db
def test_register_user_duplicate_email_conflict():
    register_user(
        email="duplicate@example.com",
        username="first_user",
        password="Password123!",
    )

    with pytest.raises(ConflictError) as exc_info:
        register_user(
            email="DUPLICATE@example.com",
            username="second_user",
            password="Password123!",
        )
    assert exc_info.value.code == "email_already_exists"


@pytest.mark.django_db
def test_register_user_duplicate_username_conflict():
    register_user(
        email="user1@example.com",
        username="unique_handle",
        password="Password123!",
    )

    with pytest.raises(ConflictError) as exc_info:
        register_user(
            email="user2@example.com",
            username="unique_handle",
            password="Password123!",
        )
    assert exc_info.value.code == "username_already_exists"


@pytest.mark.django_db
def test_register_api_endpoint():
    client = APIClient()
    payload = {
        "email": "api_user@example.com",
        "username": "api_user",
        "password": "StrongPassword123!",
        "display_name": "API User",
        "bio": "Bio from API",
    }
    response = client.post("/api/v1/auth/register/", data=payload)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["user"]["email"] == "api_user@example.com"
    assert response.data["user"]["username"] == "api_user"
    assert "X-Request-ID" in response.headers

    # Attempting duplicate registration via API returns 409 error envelope
    dup_response = client.post("/api/v1/auth/register/", data=payload)
    assert dup_response.status_code == status.HTTP_409_CONFLICT
    assert dup_response.data["error"]["code"] == "email_already_exists"
