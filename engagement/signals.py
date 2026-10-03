import logging
from typing import Any

from django.dispatch import receiver

from accounts.signals import user_deactivated

logger = logging.getLogger(__name__)


@receiver(user_deactivated)
def handle_user_deactivated(sender: Any, user_id: int, **kwargs: Any) -> None:
    """
    When an account is deactivated, permanently deletes their private bookmarks.
    Likes are preserved so post like counts remain accurate.
    """
    from engagement.models import Bookmark

    deleted_count, _ = Bookmark.objects.filter(user_id=user_id).delete()
    logger.info("Deleted %d bookmark(s) for deactivated user %d", deleted_count, user_id)
