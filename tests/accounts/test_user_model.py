import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.validators import validate_username

User = get_user_model()


@pytest.mark.django_db
def test_create_user_normalizes_email_and_username():
    user = User.objects.create_user(
        email="Alice.Smith@Example.COM",
        username="Alice_Smith",
        password="ValidPassword123!",
    )
    assert user.email == "alice.smith@example.com"
    assert user.username == "alice_smith"
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.email_verified_at is None
    assert user.deactivated_at is None
    assert user.check_password("ValidPassword123!")


@pytest.mark.django_db
def test_case_insensitive_unique_email_in_db():
    User.objects.create_user(
        email="bob@example.com",
        username="bob1",
        password="ValidPassword123!",
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            # Force raw insert bypassing clean() to verify database constraint
            User.objects.create(
                email="BOB@example.com",
                username="bob2",
            )


@pytest.mark.django_db
def test_case_insensitive_unique_username_in_db():
    User.objects.create_user(
        email="charlie1@example.com",
        username="charlie_brown",
        password="ValidPassword123!",
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            # Force raw insert bypassing clean() to verify database constraint
            User.objects.create(
                email="charlie2@example.com",
                username="CHARLIE_BROWN",
            )


def test_username_validator_reserved_names():
    for reserved in ["me", "admin", "api", "deleted", "deleted-1", "deleted-xyz"]:
        with pytest.raises(ValidationError) as exc_info:
            validate_username(reserved)
        assert exc_info.value.code == "reserved_username"


def test_username_validator_character_and_length_rules():
    invalid_usernames = [
        "ab",  # too short (< 3)
        "a" * 31,  # too long (> 30)
        "user-name",  # hyphen not allowed
        "user name",  # space not allowed
        "user@name",  # special char
        "User123",  # uppercase not allowed
    ]
    for invalid in invalid_usernames:
        with pytest.raises(ValidationError) as exc_info:
            validate_username(invalid)
        assert exc_info.value.code == "invalid_username"


@pytest.mark.django_db
def test_deactivated_check_constraint_enforced_by_db():
    user = User.objects.create_user(
        email="dave@example.com",
        username="dave_dev",
        password="ValidPassword123!",
    )

    # Violate ck_accounts_user_deactivated_inactive:
    # deactivated_at is NOT NULL while is_active is True
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            User.objects.filter(id=user.id).update(
                deactivated_at=timezone.now(),
                is_active=True,
            )

    # Valid state: deactivated_at is NOT NULL and is_active is False
    User.objects.filter(id=user.id).update(
        deactivated_at=timezone.now(),
        is_active=False,
    )
    user.refresh_from_db()
    assert user.is_deactivated is True
    assert user.is_active is False


@pytest.mark.django_db
def test_create_superuser():
    admin = User.objects.create_superuser(
        email="super@example.com",
        username="superuser",
        password="SuperPassword123!",
    )
    assert admin.is_staff is True
    assert admin.is_superuser is True
    assert admin.is_active is True
    assert admin.email_verified_at is not None
    assert admin.is_email_verified is True


def test_create_user_validations():
    with pytest.raises(ValueError, match="The Email field must be set."):
        User.objects.create_user(email="", username="test")

    with pytest.raises(ValueError, match="The Username field must be set."):
        User.objects.create_user(email="test@example.com", username="")


@pytest.mark.django_db
def test_create_superuser_validation_errors():
    with pytest.raises(ValueError, match="Superuser must have is_staff=True."):
        User.objects.create_superuser(
            email="admin@example.com",
            username="admin1",
            password="pass",
            is_staff=False,
        )

    with pytest.raises(ValueError, match="Superuser must have is_superuser=True."):
        User.objects.create_superuser(
            email="admin@example.com",
            username="admin2",
            password="pass",
            is_superuser=False,
        )


@pytest.mark.django_db
def test_user_str_and_clean():
    user = User(email="TEST@EXAMPLE.COM", username="TEST_USER")
    assert str(user) == "TEST_USER"
    user.clean()
    assert user.email == "test@example.com"
    assert user.username == "test_user"


def test_argon2_is_first_hasher_in_base_settings():
    from config.settings.base import PASSWORD_HASHERS

    assert PASSWORD_HASHERS[0] == "django.contrib.auth.hashers.Argon2PasswordHasher"
