import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient

from accounts.models import RefreshTokenRecord
from accounts.services import (
    login_user,
    logout_user,
    register_user,
    rotate_refresh_token,
)

User = get_user_model()


@pytest.mark.django_db
def test_login_success():
    user, _ = register_user(
        email="auth_test@example.com",
        username="auth_test_user",
        password="ValidPassword123!",
    )

    access, refresh, logged_in_user = login_user(
        email="auth_test@example.com",
        password="ValidPassword123!",
        user_agent="Mozilla/5.0 Test",
    )

    assert logged_in_user.id == user.id
    assert access and isinstance(access, str)
    assert refresh and isinstance(refresh, str)

    # Check that RefreshTokenRecord was created in DB
    records = RefreshTokenRecord.objects.filter(user=user)
    assert records.count() == 1
    record = records.first()
    assert record.revoked_at is None
    assert record.user_agent == "Mozilla/5.0 Test"
    assert record.family_id is not None


@pytest.mark.django_db
def test_login_invalid_password():
    register_user(
        email="wrong_pass@example.com",
        username="wrong_pass_user",
        password="CorrectPassword123!",
    )

    with pytest.raises(AuthenticationFailed) as exc_info:
        login_user("wrong_pass@example.com", "WrongPassword123!")
    assert exc_info.value.detail.code == "authentication_failed"


@pytest.mark.django_db
def test_refresh_token_rotation_and_record_tracking():
    user, _ = register_user(
        email="rotate_test@example.com",
        username="rotate_user",
        password="Password123!",
    )

    _, original_refresh, _ = login_user("rotate_test@example.com", "Password123!")

    initial_record = RefreshTokenRecord.objects.get(user=user)
    initial_family_id = initial_record.family_id

    # Rotate refresh token
    new_access, new_refresh = rotate_refresh_token(original_refresh)
    assert new_access and new_refresh
    assert new_refresh != original_refresh

    initial_record.refresh_from_db()
    assert initial_record.revoked_at is not None
    assert initial_record.revoke_reason == "rotated"
    assert initial_record.replaced_by is not None

    # Verify newly created record is part of the same family
    new_record = RefreshTokenRecord.objects.get(jti=initial_record.replaced_by.jti)
    assert new_record.family_id == initial_family_id
    assert new_record.family_started_at == initial_record.family_started_at
    assert new_record.revoked_at is None


@pytest.mark.django_db
def test_refresh_token_reuse_detection_revokes_entire_family():
    user, _ = register_user(
        email="reuse_test@example.com",
        username="reuse_user",
        password="Password123!",
    )

    _, first_refresh, _ = login_user("reuse_test@example.com", "Password123!")

    # Legitimate first rotation
    _, second_refresh = rotate_refresh_token(first_refresh)

    # Legitimate second rotation
    _, third_refresh = rotate_refresh_token(second_refresh)

    # An attacker replays first_refresh (which was already rotated!)
    with pytest.raises(AuthenticationFailed) as exc_info:
        rotate_refresh_token(first_refresh)
    assert exc_info.value.detail.code == "token_reuse_detected"

    # Verify ALL records in that family are now revoked with reuse_detected
    family_records = RefreshTokenRecord.objects.filter(user=user)
    for rec in family_records:
        assert rec.revoked_at is not None

    # Even the latest third_refresh is now rejected because the entire family was compromised
    with pytest.raises(AuthenticationFailed):
        rotate_refresh_token(third_refresh)


@pytest.mark.django_db
def test_logout_revokes_token():
    user, _ = register_user(
        email="logout_test@example.com",
        username="logout_user",
        password="Password123!",
    )

    _, refresh, _ = login_user("logout_test@example.com", "Password123!")
    record = RefreshTokenRecord.objects.get(user=user)
    assert record.revoked_at is None

    logout_user(refresh)
    record.refresh_from_db()
    assert record.revoked_at is not None
    assert record.revoke_reason == "logout"


@pytest.mark.django_db
def test_auth_api_flow():
    client = APIClient()
    register_user(
        email="api_auth@example.com",
        username="api_auth_user",
        password="ValidPassword123!",
    )

    # 1. Login
    login_resp = client.post(
        "/api/v1/auth/login/",
        data={"email": "api_auth@example.com", "password": "ValidPassword123!"},
    )
    assert login_resp.status_code == status.HTTP_200_OK
    access = login_resp.data["access"]
    refresh = login_resp.data["refresh"]
    assert access and refresh

    # 2. Rotate token
    refresh_resp = client.post("/api/v1/auth/refresh/", data={"refresh": refresh})
    assert refresh_resp.status_code == status.HTTP_200_OK
    new_access = refresh_resp.data["access"]
    new_refresh = refresh_resp.data["refresh"]

    # 3. Logout with authenticated client
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access}")
    logout_resp = client.post("/api/v1/auth/logout/", data={"refresh": new_refresh})
    assert logout_resp.status_code == status.HTTP_200_OK
