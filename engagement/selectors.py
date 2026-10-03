from typing import Any

from django.db.models import QuerySet

from engagement.models import Bookmark, Like


def list_user_bookmarks(user: Any) -> QuerySet[Bookmark]:
    """
    Returns the user's private bookmarks for published posts,
    ordered by -created_at, -id (served by idx_bookmark_user_feed).
    """
    return (
        Bookmark.objects.filter(user=user, post__status="published")
        .select_related("post", "post__author", "post__author__profile", "post__category")
        .order_by("-created_at", "-id")
    )


def has_user_liked_post(user: Any, post_id: int) -> bool:
    """Returns True if user has liked the post, False otherwise."""
    if not user or not user.is_authenticated:
        return False
    return Like.objects.filter(user=user, post_id=post_id).exists()


def has_user_bookmarked_post(user: Any, post_id: int) -> bool:
    """Returns True if user has bookmarked the post, False otherwise."""
    if not user or not user.is_authenticated:
        return False
    return Bookmark.objects.filter(user=user, post_id=post_id).exists()
