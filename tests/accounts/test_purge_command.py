import io
import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from accounts.models import RefreshTokenRecord

User = get_user_model()


@pytest.mark.django_db
def test_purge_expired_tokens_command():
    user = User.objects.create_user(
        email="purge_user@example.com",
        username="purge_user",
        password="Password123!",
    )
    now = timezone.now()

    # 1. Record expired 10 days ago and revoked -> should be purged
    RefreshTokenRecord.objects.create(
        user=user,
        jti=uuid.uuid4(),
        family_id=uuid.uuid4(),
        family_started_at=now - timedelta(days=20),
        issued_at=now - timedelta(days=20),
        expires_at=now - timedelta(days=10),
        revoked_at=now - timedelta(days=10),
        revoke_reason="rotated",
    )

    # 2. Record expired 2 days ago and revoked -> within 7 day retention window, NOT purged
    RefreshTokenRecord.objects.create(
        user=user,
        jti=uuid.uuid4(),
        family_id=uuid.uuid4(),
        family_started_at=now - timedelta(days=5),
        issued_at=now - timedelta(days=5),
        expires_at=now - timedelta(days=2),
        revoked_at=now - timedelta(days=2),
        revoke_reason="rotated",
    )

    # 3. Active record -> NOT purged
    RefreshTokenRecord.objects.create(
        user=user,
        jti=uuid.uuid4(),
        family_id=uuid.uuid4(),
        family_started_at=now,
        issued_at=now,
        expires_at=now + timedelta(days=7),
        revoked_at=None,
    )

    assert RefreshTokenRecord.objects.count() == 3

    out = io.StringIO()
    call_command("purge_expired_tokens", retention_days=7, stdout=out)

    assert "Successfully purged 1 expired refresh token records" in out.getvalue()
    assert RefreshTokenRecord.objects.count() == 2
