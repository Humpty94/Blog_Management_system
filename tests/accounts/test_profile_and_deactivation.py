from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import EmailVerificationToken, Profile, RefreshTokenRecord
from accounts.services import deactivate_user, login_user, register_user
from accounts.signals import user_deactivated
from common.exceptions import ApplicationError

User = get_user_model()


@pytest.mark.django_db
def test_current_user_profile_crud():
    user, _ = register_user(
        email="profile_crud@example.com",
        username="profile_crud_user",
        password="Password123!",
        display_name="Initial Name",
        bio="Initial Bio",
    )
    access, _, _ = login_user("profile_crud@example.com", "Password123!")

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    # Read profile
    get_resp = client.get("/api/v1/users/me/")
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.data["username"] == "profile_crud_user"
    assert get_resp.data["email"] == "profile_crud@example.com"
    assert get_resp.data["display_name"] == "Initial Name"
    assert get_resp.data["bio"] == "Initial Bio"
    assert get_resp.data["is_email_verified"] is False

    # Update profile
    patch_resp = client.patch(
        "/api/v1/users/me/",
        data={"display_name": "Updated Name", "bio": "Updated Bio"},
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    assert patch_resp.data["display_name"] == "Updated Name"
    assert patch_resp.data["bio"] == "Updated Bio"


@pytest.mark.django_db
def test_public_user_profile_read():
    client = APIClient()
    register_user(
        email="public_author@example.com",
        username="public_author",
        password="Password123!",
        display_name="Public Author",
        bio="Public Author Bio",
    )

    # Public profile read does not require authentication and omits email
    resp = client.get("/api/v1/users/public_author/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["username"] == "public_author"
    assert resp.data["display_name"] == "Public Author"
    assert resp.data["bio"] == "Public Author Bio"
    assert "email" not in resp.data

    # Non-existent user returns 404
    not_found_resp = client.get("/api/v1/users/non_existent/")
    assert not_found_resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_account_deactivation_anonymization_and_resource_cleanup():
    user, _ = register_user(
        email="to_be_deleted@example.com",
        username="to_be_deleted",
        password="Password123!",
        display_name="Doomed Name",
        bio="Doomed Bio",
    )
    _, _, _ = login_user("to_be_deleted@example.com", "Password123!")

    user_id = user.id

    # Mock receiver to verify signal dispatch
    mock_receiver = MagicMock()
    user_deactivated.connect(mock_receiver)

    try:
        # Invalid password confirmation fails
        with pytest.raises(ApplicationError) as exc_info:
            deactivate_user(user, "WrongPassword!")
        assert exc_info.value.code == "invalid_password"

        # Correct password deactivates account
        deactivate_user(user, "Password123!")

        # Verify signal was called with correct parameters
        mock_receiver.assert_called_once()
        _, kwargs = mock_receiver.call_args
        assert kwargs["user_id"] == user_id

        # Verify user row anonymized in place
        user.refresh_from_db()
        assert user.is_active is False
        assert user.deactivated_at is not None
        assert user.is_deactivated is True
        assert user.email == f"deleted-{user_id}@deleted.invalid"
        assert user.username == f"deleted-{user_id}"
        assert not user.has_usable_password()

        # Verify profile cleared
        profile = Profile.objects.get(user=user)
        assert profile.display_name == ""
        assert profile.bio == ""

        # Verify email verification tokens purged
        assert EmailVerificationToken.objects.filter(user=user).count() == 0

        # Verify refresh tokens marked deactivated
        tokens = RefreshTokenRecord.objects.filter(user=user)
        for tok in tokens:
            assert tok.revoked_at is not None
            assert tok.revoke_reason == "deactivated"

        # Verify released original username and email can be registered immediately
        new_user, _ = register_user(
            email="to_be_deleted@example.com",
            username="to_be_deleted",
            password="NewPassword123!",
        )
        assert new_user.id != user_id
        assert new_user.email == "to_be_deleted@example.com"
        assert new_user.username == "to_be_deleted"

    finally:
        user_deactivated.disconnect(mock_receiver)


@pytest.mark.django_db
def test_deactivate_api_endpoint():
    user, _ = register_user(
        email="api_deactivate@example.com",
        username="api_deactivate_user",
        password="ValidPassword123!",
    )
    access, _, _ = login_user("api_deactivate@example.com", "ValidPassword123!")

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    resp = client.post("/api/v1/users/me/deactivate/", data={"password": "ValidPassword123!"})
    assert resp.status_code == status.HTTP_200_OK
    assert "permanently deactivated" in resp.data["message"]

    # Public profile for deactivated user is no longer accessible
    client.credentials()
    pub_resp = client.get("/api/v1/users/api_deactivate_user/")
    assert pub_resp.status_code == status.HTTP_404_NOT_FOUND
