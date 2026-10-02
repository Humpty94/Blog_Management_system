import logging
from typing import Any

from django.db import transaction
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from blog.selectors import get_published_post_or_404
from comments.models import Comment
from common.exceptions import ApplicationError

logger = logging.getLogger(__name__)


def create_comment(
    post_slug_or_id: str | int,
    author: Any,
    body: str,
    parent_id: int | None = None,
) -> Comment:
    """
    Creates a new comment or a one-level reply on a published post.
    Enforces the single-reply-level rule and ensures replies target valid,
    non-deleted root comments belonging to the same post.
    """
    post = get_published_post_or_404(post_slug_or_id)

    clean_body = body.strip()
    if not clean_body:
        raise ApplicationError(
            "Comment body cannot be blank.",
            code="blank_comment",
            status_code=400,
        )
    if len(clean_body) > 2000:
        raise ApplicationError(
            "Comment body cannot exceed 2000 characters.",
            code="comment_too_long",
            status_code=400,
        )

    with transaction.atomic():
        if parent_id is not None:
            try:
                parent = Comment.objects.select_for_update().get(id=parent_id)
            except Comment.DoesNotExist:
                raise ApplicationError(
                    "Parent comment not found.",
                    code="parent_not_found",
                    status_code=404,
                ) from None

            if parent.post_id != post.id:
                raise ApplicationError(
                    "Parent comment belongs to a different post.",
                    code="cross_post_reply",
                    status_code=400,
                )

            # Exactly one reply level invariant
            if parent.parent_id is not None:
                raise ApplicationError(
                    "Nested replies are not permitted. You can only reply to a root comment.",
                    code="nested_replies_not_allowed",
                    status_code=400,
                )

            if parent.is_deleted:
                raise ApplicationError(
                    "Cannot reply to a deleted comment.",
                    code="cannot_reply_to_deleted",
                    status_code=400,
                )

        comment = Comment.objects.create(
            post=post,
            author=author,
            parent_id=parent_id,
            body=clean_body,
            is_deleted=False,
            deleted_at=None,
        )
        return comment


def delete_comment(comment_id: int, user: Any) -> None:
    """
    Deletes a comment adhering to placeholder vs hard-delete semantics:
    - Replies are hard deleted.
    - Root comments without replies are hard deleted.
    - Root comments with replies are converted to placeholders (is_deleted=True, body='').
    - Deleting an existing placeholder is idempotent (204, no changes).
    """
    with transaction.atomic():
        try:
            comment = Comment.objects.select_for_update().get(id=comment_id)
        except Comment.DoesNotExist:
            raise Http404("Comment not found.") from None

        if comment.author_id != user.id:
            raise PermissionDenied("You do not have permission to delete this comment.")

        # Idempotent deletion of existing placeholder
        if comment.is_deleted:
            return

        # Reply deletion: always hard delete
        if comment.parent_id is not None:
            comment.delete()
            return

        # Root deletion: check for child replies
        has_replies = comment.replies.exists()
        if not has_replies:
            comment.delete()
        else:
            comment.is_deleted = True
            comment.body = ""
            comment.deleted_at = timezone.now()
            comment.save(update_fields=["is_deleted", "body", "deleted_at", "updated_at"])
