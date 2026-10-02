import logging
from typing import Any

from django.dispatch import receiver

from accounts.signals import user_deactivated

logger = logging.getLogger(__name__)


@receiver(user_deactivated)
def handle_user_deactivated(sender: Any, user_id: int, **kwargs: Any) -> None:
    """
    When an account is deactivated, permanently deletes their private drafts.
    Published posts are preserved (attributed to the anonymized user).
    """
    from blog.models import Post

    deleted_count, _ = Post.objects.filter(author_id=user_id, status="draft").delete()
    logger.info("Deleted %d draft post(s) for deactivated user %d", deleted_count, user_id)
