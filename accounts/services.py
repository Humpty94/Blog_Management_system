import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from accounts.models import EmailVerificationToken, Profile, RefreshTokenRecord
from accounts.signals import user_deactivated
from accounts.validators import validate_username
from common.exceptions import ApplicationError, ConflictError

logger = logging.getLogger(__name__)
User = get_user_model()

# Token lifetime configurations
ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
REFRESH_TOKEN_SLIDING_WINDOW = timedelta(days=7)
REFRESH_FAMILY_ABSOLUTE_LIFETIME = timedelta(days=30)
VERIFICATION_TOKEN_LIFETIME = timedelta(hours=24)


def create_email_verification_token(user: User) -> tuple[str, EmailVerificationToken]:
    """
    Generates a secure random verification token and stores its SHA-256 hash.
    Returns (raw_token, token_record).
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = timezone.now() + VERIFICATION_TOKEN_LIFETIME

    token_record = EmailVerificationToken.objects.create(
        user=user,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    return raw_token, token_record


def send_verification_email(user: User, raw_token: str) -> None:
    """
    Dispatches the email verification link/token using Django's email backend.
    """
    subject = "Verify your email address"
    message = (
        f"Hello {user.username},\n\n"
        f"Please verify your email address using this verification token:\n"
        f"{raw_token}\n\n"
        f"This token will expire in 24 hours."
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
        recipient_list=[user.email],
        fail_silently=True,
    )


def register_user(
    email: str,
    username: str,
    password: str,
    display_name: str = "",
    bio: str = "",
) -> tuple[User, str]:
    """
    Registers a new user, provisions their 1:1 Profile atomically,
    and generates an email verification token.
    """
    validate_username(username)
    normalized_email = email.strip().lower()
    normalized_username = username.strip().lower()

    if User.objects.filter(email=normalized_email).exists():
        raise ConflictError(
            "An account with this email already exists.",
            code="email_already_exists",
        )
    if User.objects.filter(username=normalized_username).exists():
        raise ConflictError(
            "An account with this username already exists.",
            code="username_already_exists",
        )

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=normalized_email,
                username=normalized_username,
                password=password,
            )
            Profile.objects.create(
                user=user,
                display_name=display_name.strip() if display_name else "",
                bio=bio.strip() if bio else "",
            )
            raw_token, _ = create_email_verification_token(user)
    except IntegrityError as exc:
        raise ConflictError(
            "An account with this email or username already exists.",
            code="account_conflict",
        ) from exc

    # Send verification email after atomic block
    send_verification_email(user, raw_token)
    return user, raw_token


def verify_email(raw_token: str) -> User:
    """
    Validates a raw verification token by checking its SHA-256 hash.
    Marks the token used and updates email_verified_at.
    """
    if not raw_token:
        raise ApplicationError("Verification token is required.", code="missing_token")

    token_hash = hashlib.sha256(raw_token.strip().encode()).hexdigest()
    now = timezone.now()

    token_record = (
        EmailVerificationToken.objects.select_related("user").filter(token_hash=token_hash).first()
    )

    if not token_record or token_record.used_at is not None or token_record.expires_at <= now:
        raise ApplicationError(
            "Verification token is invalid or has expired.",
            code="invalid_verification_token",
            status_code=400,
        )

    user = token_record.user
    with transaction.atomic():
        token_record.used_at = now
        token_record.save(update_fields=["used_at"])

        if user.email_verified_at is None:
            user.email_verified_at = now
            user.save(update_fields=["email_verified_at"])

    return user


def resend_verification_email(email: str) -> str | None:
    """
    Invalidates previous unused verification tokens for the user,
    issues a new one, and sends an email.
    """
    normalized_email = email.strip().lower()
    user = User.objects.filter(email=normalized_email).first()

    if not user or not user.is_active or user.is_email_verified or user.is_deactivated:
        # Avoid leaking user presence
        return None

    now = timezone.now()
    with transaction.atomic():
        # Invalidate all prior unused tokens
        EmailVerificationToken.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
        raw_token, _ = create_email_verification_token(user)

    send_verification_email(user, raw_token)
    return raw_token


def issue_token_pair_for_user(
    user: User,
    user_agent: str = "",
    family_id: uuid.UUID | None = None,
    family_started_at: datetime | None = None,
) -> tuple[str, str, RefreshTokenRecord]:
    """
    Issues a JWT access token and refresh token pair, recording the refresh token
    in RefreshTokenRecord with family tracking and sliding/absolute expiration.
    """
    now = timezone.now()
    if family_id is None:
        family_id = uuid.uuid4()
        family_started_at = now
    elif family_started_at is None:
        family_started_at = now

    # Expiration is the lesser of the sliding inactivity window and absolute family cap
    sliding_expiry = now + REFRESH_TOKEN_SLIDING_WINDOW
    absolute_expiry = family_started_at + REFRESH_FAMILY_ABSOLUTE_LIFETIME
    refresh_expires_at = min(sliding_expiry, absolute_expiry)

    # SimpleJWT token setup
    refresh = RefreshToken.for_user(user)
    refresh.set_exp(lifetime=(refresh_expires_at - now))
    jti = uuid.UUID(str(refresh["jti"]))

    # Attach claims to token
    refresh["family_id"] = str(family_id)
    refresh["family_started_at"] = family_started_at.isoformat()

    access = refresh.access_token
    access.set_exp(lifetime=ACCESS_TOKEN_LIFETIME)

    record = RefreshTokenRecord.objects.create(
        jti=jti,
        family_id=family_id,
        family_started_at=family_started_at,
        user=user,
        issued_at=now,
        expires_at=refresh_expires_at,
        user_agent=user_agent[:255] if user_agent else "",
    )

    return str(access), str(refresh), record


def login_user(
    email: str,
    password: str,
    user_agent: str = "",
) -> tuple[str, str, User]:
    """
    Authenticates user credentials and establishes a new refresh token family.
    """
    normalized_email = email.strip().lower()
    user = authenticate(email=normalized_email, password=password)

    if not user or not user.is_active:
        raise AuthenticationFailed(
            "Invalid email or password.",
            code="authentication_failed",
        )

    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])

    access_token, refresh_token, _ = issue_token_pair_for_user(
        user=user,
        user_agent=user_agent,
    )
    return access_token, refresh_token, user


def rotate_refresh_token(
    refresh_token_str: str,
    user_agent: str = "",
) -> tuple[str, str]:
    """
    Rotates a refresh token: invalidates old token, checks for reuse theft,
    and issues a new token pair within the same session family.
    """
    try:
        token = RefreshToken(refresh_token_str)
        jti_str = token.get("jti")
        jti = uuid.UUID(str(jti_str))
    except (TokenError, ValueError, KeyError) as exc:
        raise AuthenticationFailed("Token is invalid or expired.", code="token_invalid") from exc

    now = timezone.now()
    record = RefreshTokenRecord.objects.select_related("user").filter(jti=jti).first()

    if not record:
        raise AuthenticationFailed("Token is invalid.", code="token_invalid")

    # Reuse detection: an already-revoked refresh token was presented
    if record.revoked_at is not None:
        logger.warning(
            "Refresh token reuse detected for family %s. Revoking all family tokens.",
            record.family_id,
        )
        RefreshTokenRecord.objects.filter(
            family_id=record.family_id,
            revoked_at__isnull=True,
        ).update(
            revoked_at=now,
            revoke_reason="reuse_detected",
        )
        raise AuthenticationFailed(
            "Token reuse detected. All sessions in this family have been terminated.",
            code="token_reuse_detected",
        )

    # Check expiration
    if record.expires_at <= now:
        raise AuthenticationFailed("Token has expired.", code="token_expired")

    if now >= record.family_started_at + REFRESH_FAMILY_ABSOLUTE_LIFETIME:
        raise AuthenticationFailed(
            "Session has reached maximum allowed lifetime. Please log in again.",
            code="session_expired",
        )

    if not record.user.is_active:
        raise AuthenticationFailed("User account is inactive.", code="user_inactive")

    with transaction.atomic():
        new_access, new_refresh, new_record = issue_token_pair_for_user(
            user=record.user,
            user_agent=user_agent,
            family_id=record.family_id,
            family_started_at=record.family_started_at,
        )
        record.revoked_at = now
        record.revoke_reason = "rotated"
        record.replaced_by = new_record
        record.save(update_fields=["revoked_at", "revoke_reason", "replaced_by"])

    return new_access, new_refresh


def logout_user(refresh_token_str: str) -> None:
    """
    Revokes the specific refresh token upon user logout.
    """
    try:
        token = RefreshToken(refresh_token_str)
        jti = uuid.UUID(str(token.get("jti")))
    except Exception:
        return

    RefreshTokenRecord.objects.filter(jti=jti, revoked_at__isnull=True).update(
        revoked_at=timezone.now(),
        revoke_reason="logout",
    )


def deactivate_user(user: User, password: str) -> None:
    """
    Permanently deactivates and anonymizes a user in place.
    Fires the synchronous user_deactivated signal inside the transaction.
    """
    if not user.check_password(password):
        raise ApplicationError(
            "Incorrect password confirmation.",
            code="invalid_password",
            status_code=400,
        )

    if user.is_deactivated:
        raise ApplicationError(
            "Account has already been deactivated.",
            code="already_deactivated",
            status_code=400,
        )

    now = timezone.now()
    with transaction.atomic():
        # Anonymize user fields in place, releasing original email and username
        user.email = f"deleted-{user.id}@deleted.invalid"
        user.username = f"deleted-{user.id}"
        user.is_active = False
        user.deactivated_at = now
        user.set_unusable_password()
        user.save(
            update_fields=[
                "email",
                "username",
                "is_active",
                "deactivated_at",
                "password",
            ]
        )

        # Redact profile
        Profile.objects.filter(user=user).update(display_name="", bio="")

        # Hard-delete email verification tokens
        EmailVerificationToken.objects.filter(user=user).delete()

        # Revoke all active refresh sessions
        RefreshTokenRecord.objects.filter(user=user, revoked_at__isnull=True).update(
            revoked_at=now,
            revoke_reason="deactivated",
        )

        # Synchronously notify downstream apps (blog deletes drafts, engagement deletes bookmarks)
        user_deactivated.send(sender=User, user_id=user.id, user=user)

    logger.info("User %s successfully deactivated and anonymized.", user.id)
