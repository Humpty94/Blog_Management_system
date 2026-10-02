from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from accounts.managers import UserManager
from accounts.validators import validate_username
from common.models import TimestampedModel


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model where email is the primary login credential.
    Implements case-insensitive uniqueness, soft-deactivation tracking,
    and verified-email timestamping.
    """

    id = models.BigAutoField(primary_key=True)
    email = models.EmailField(max_length=254, unique=True)
    username = models.CharField(
        max_length=30,
        unique=True,
        validators=[validate_username],
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "accounts_user"
        verbose_name = "user"
        verbose_name_plural = "users"
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="uq_accounts_user_lower_email",
            ),
            models.UniqueConstraint(
                Lower("username"),
                name="uq_accounts_user_lower_username",
            ),
            models.CheckConstraint(
                condition=models.Q(deactivated_at__isnull=True) | models.Q(is_active=False),
                name="ck_accounts_user_deactivated_inactive",
            ),
        ]

    def __str__(self):
        return self.username

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.lower().strip()
        if self.username:
            self.username = self.username.lower().strip()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower().strip()
        if self.username:
            self.username = self.username.lower().strip()
        super().save(*args, **kwargs)

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def is_deactivated(self) -> bool:
        return self.deactivated_at is not None


class Profile(TimestampedModel):
    """
    Public presentation metadata for a User.
    Created explicitly during registration in the same transaction.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="profile",
    )
    display_name = models.CharField(max_length=80, blank=True, default="")
    bio = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "accounts_profile"
        verbose_name = "profile"
        verbose_name_plural = "profiles"

    def __str__(self):
        return f"Profile of {self.user.username}"

    @property
    def effective_display_name(self) -> str:
        return self.display_name if self.display_name else self.user.username


class EmailVerificationToken(models.Model):
    """
    Single-use proof of email ownership.
    Raw random token is sent to the user; only SHA-256 hex is persisted.
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_emailverificationtoken"
        verbose_name = "email verification token"
        verbose_name_plural = "email verification tokens"
        constraints = [
            models.UniqueConstraint(
                fields=["token_hash"],
                name="uq_email_verification_token_hash",
            ),
            models.CheckConstraint(
                condition=models.Q(expires_at__gt=models.F("created_at")),
                name="ck_email_verification_expires_after_created",
            ),
        ]

    def __str__(self):
        return f"Verification token for {self.user.email}"

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and timezone.now() < self.expires_at


class RefreshTokenRecord(models.Model):
    """
    Server-side record of issued refresh tokens with token family tracking,
    rotation, and reuse detection.
    """

    REVOKE_REASONS = (
        ("rotated", "Rotated"),
        ("logout", "Logout"),
        ("reuse_detected", "Reuse Detected"),
        ("deactivated", "Deactivated"),
    )

    id = models.BigAutoField(primary_key=True)
    jti = models.UUIDField(unique=True, db_index=True)
    family_id = models.UUIDField(db_index=True)
    family_started_at = models.DateTimeField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
    )
    issued_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoke_reason = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=REVOKE_REASONS,
    )
    replaced_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replaces",
    )
    user_agent = models.CharField(max_length=255, default="", blank=True)

    class Meta:
        db_table = "accounts_refreshtokenrecord"
        verbose_name = "refresh token record"
        verbose_name_plural = "refresh token records"
        indexes = [
            models.Index(fields=["family_id"], name="idx_refresh_token_family_id"),
            models.Index(fields=["user_id"], name="idx_refresh_token_user_id"),
            models.Index(fields=["expires_at"], name="idx_refresh_token_expires_at"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["jti"],
                name="uq_refresh_token_record_jti",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(revoked_at__isnull=True, revoke_reason__isnull=True)
                    | models.Q(revoked_at__isnull=False, revoke_reason__isnull=False)
                ),
                name="ck_refresh_token_revoked_reason_sync",
            ),
            models.CheckConstraint(
                condition=models.Q(revoke_reason__isnull=True)
                | models.Q(
                    revoke_reason__in=[
                        "rotated",
                        "logout",
                        "reuse_detected",
                        "deactivated",
                    ]
                ),
                name="ck_refresh_token_revoke_reason_choices",
            ),
        ]

    def __str__(self):
        return f"RefreshTokenRecord(jti={self.jti}, family={self.family_id})"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and timezone.now() < self.expires_at
