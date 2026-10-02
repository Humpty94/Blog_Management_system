import secrets
import string

from django.utils.text import slugify

BASE36_ALPHABET = string.digits + string.ascii_lowercase


def generate_random_suffix(length: int = 8) -> str:
    """Generates a random lowercase base36 suffix."""
    return "".join(secrets.choice(BASE36_ALPHABET) for _ in range(length))


def generate_post_slug(title: str) -> str:
    """
    Generates a unique, URL-safe slug for a post.
    Format: slugify(title)[:60] + '-' + 8-char random base36 suffix.
    If slugify yields nothing, uses 'post' as the base.
    """
    base_slug = slugify(title)[:60].strip("-")
    if not base_slug:
        base_slug = "post"

    suffix = generate_random_suffix(8)
    return f"{base_slug}-{suffix}"
