from django.contrib.auth import get_user_model

from accounts.models import Profile

User = get_user_model()


def get_user_by_id(user_id: int) -> User | None:
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None


def get_user_by_email(email: str) -> User | None:
    if not email:
        return None
    try:
        return User.objects.get(email=email.strip().lower())
    except User.DoesNotExist:
        return None


def get_user_by_username(username: str) -> User | None:
    if not username:
        return None
    try:
        return User.objects.get(username=username.strip().lower())
    except User.DoesNotExist:
        return None


def get_profile_by_user(user: User) -> Profile | None:
    try:
        return Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        return None


def get_active_profile_by_username(username: str) -> Profile | None:
    if not username:
        return None
    try:
        return (
            Profile.objects.select_related("user")
            .filter(user__username=username.strip().lower(), user__is_active=True)
            .get()
        )
    except Profile.DoesNotExist:
        return None
