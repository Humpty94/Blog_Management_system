import re

from django.core.exceptions import ValidationError

RESERVED_USERNAMES = frozenset({"me", "admin", "api", "deleted"})
USERNAME_REGEX = re.compile(r"^[a-z0-9_]{3,30}$")


def validate_username(value: str) -> None:
    """
    Validates that a username meets character, length, and reservation constraints:
    - Length: 3 to 30 characters
    - Characters: lowercase ASCII letters, digits, underscores only
    - Reserved values: 'me', 'admin', 'api', 'deleted', and any prefix starting with 'deleted-'
    """
    if not value:
        raise ValidationError("Username cannot be empty.", code="invalid_username")

    normalized = value.strip().lower()

    # Reserved check must take precedence
    if normalized in RESERVED_USERNAMES or normalized.startswith("deleted-"):
        raise ValidationError(
            f"The username '{normalized}' is reserved and cannot be registered.",
            code="reserved_username",
        )

    # Enforce strict lowercase regex format directly on input value
    if not USERNAME_REGEX.match(value):
        raise ValidationError(
            "Username must be between 3 and 30 characters and contain "
            "only lowercase letters, numbers, and underscores.",
            code="invalid_username",
        )
