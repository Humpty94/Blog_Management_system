from django.conf import settings
from django.db import models
from django.utils import timezone


class Like(models.Model):
    """
    Records a user liking a published blog post.
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    post = models.ForeignKey(
        "blog.Post",
        on_delete=models.CASCADE,
        related_name="likes",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "engagement_like"
        verbose_name = "like"
        verbose_name_plural = "likes"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="uq_like_user_post",
            ),
        ]
        indexes = [
            models.Index(fields=["post"], name="idx_like_post"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} likes post {self.post_id}"


class Bookmark(models.Model):
    """
    Records a user privately saving a published blog post.
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    post = models.ForeignKey(
        "blog.Post",
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "engagement_bookmark"
        verbose_name = "bookmark"
        verbose_name_plural = "bookmarks"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="uq_bookmark_user_post",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-created_at", "-id"], name="idx_bookmark_user_feed"),
            models.Index(fields=["post"], name="idx_bookmark_post"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} bookmarked post {self.post_id}"
