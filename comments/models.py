from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Length, Trim
from django.db.models.lookups import GreaterThan, LessThanOrEqual

from common.models import TimestampedModel


class Comment(TimestampedModel):
    """
    Comment on a published blog post, supporting exactly one reply level.
    Deletions are either hard deletes or soft placeholders when replies exist.
    """

    id = models.BigAutoField(primary_key=True)
    post = models.ForeignKey(
        "blog.Post",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="comments",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    body = models.TextField()
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "comments_comment"
        verbose_name = "comment"
        verbose_name_plural = "comments"
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(parent=F("id")),
                name="ck_comment_not_self_parent",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_deleted=True, deleted_at__isnull=False)
                    | Q(is_deleted=False, deleted_at__isnull=True)
                ),
                name="ck_comment_deleted_state",
            ),
            models.CheckConstraint(
                condition=Q(is_deleted=True) | GreaterThan(Length(Trim("body")), 0),
                name="ck_comment_not_blank_unless_deleted",
            ),
            models.CheckConstraint(
                condition=LessThanOrEqual(Length("body"), 2000),
                name="ck_comment_body_len",
            ),
        ]
        indexes = [
            models.Index(
                fields=["post", "created_at", "id"],
                name="idx_comment_roots",
                condition=Q(parent__isnull=True),
            ),
            models.Index(
                fields=["parent", "created_at", "id"],
                name="idx_comment_replies",
                condition=Q(parent__isnull=False),
            ),
        ]

    def __str__(self) -> str:
        if self.is_deleted:
            return f"Comment {self.id} (Deleted)"
        preview = self.body[:30].strip()
        return f"Comment {self.id} by {self.author.username}: {preview}..."

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    @property
    def is_reply(self) -> bool:
        return self.parent_id is not None
