from typing import Any

from django.db import transaction

from blog.models import Post
from blog.selectors import get_published_post_or_404
from blog.services import adjust_post_like_count
from common.exceptions import ApplicationError
from engagement.models import Bookmark, Like


def like_post(post_slug_or_id: str | int, user: Any) -> tuple[Post, bool]:
    """
    Likes a published post for the user.
    Enforces self-like prohibition: authors cannot like their own posts.
    Idempotent: repeated calls do not duplicate likes or increment counter further.
    """
    post = get_published_post_or_404(post_slug_or_id)

    if post.author_id == user.id:
        raise ApplicationError(
            "Authors cannot like their own posts.",
            code="self_like_prohibited",
            status_code=400,
        )

    with transaction.atomic():
        like, created = Like.objects.get_or_create(user=user, post=post)
        if created:
            adjust_post_like_count(post_id=post.id, delta=1)
            post.refresh_from_db(fields=["like_count"])

    return post, created


def unlike_post(post_slug_or_id: str | int, user: Any) -> tuple[Post, bool]:
    """
    Removes a user's like from a published post.
    Idempotent: unliking a post that is not liked succeeds without changing counter.
    """
    post = get_published_post_or_404(post_slug_or_id)

    with transaction.atomic():
        deleted_count, _ = Like.objects.filter(user=user, post=post).delete()
        if deleted_count > 0:
            adjust_post_like_count(post_id=post.id, delta=-1)
            post.refresh_from_db(fields=["like_count"])

    return post, deleted_count > 0


def bookmark_post(post_slug_or_id: str | int, user: Any) -> tuple[Bookmark, bool]:
    """
    Privately bookmarks a published post for the user.
    Author bookmarking own post is permitted; bookmarking drafts is prohibited.
    Idempotent: repeated calls do not create duplicates.
    """
    post = get_published_post_or_404(post_slug_or_id)

    with transaction.atomic():
        bookmark, created = Bookmark.objects.get_or_create(user=user, post=post)

    return bookmark, created


def unbookmark_post(post_slug_or_id: str | int, user: Any) -> bool:
    """
    Removes a post from the user's private bookmarks.
    Idempotent: removing a non-existent bookmark succeeds without error.
    """
    post = get_published_post_or_404(post_slug_or_id)

    deleted_count, _ = Bookmark.objects.filter(user=user, post=post).delete()
    return deleted_count > 0
