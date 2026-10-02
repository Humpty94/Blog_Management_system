import logging
from typing import Any

from django.contrib.postgres.search import SearchVector
from django.db import IntegrityError, models, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from blog.content import extract_plain_text, generate_excerpt
from blog.models import Category, Post
from blog.utils import generate_post_slug
from common.exceptions import ApplicationError, EmailNotVerifiedError

logger = logging.getLogger(__name__)


def create_post(
    author: Any,
    category: Category,
    title: str,
    content_markdown: str = "",
) -> Post:
    """
    Creates a new draft post with an immutable slug, derived plain text,
    server-generated excerpt, and initial search vector.
    """
    title = title.strip()
    if len(title) < 3:
        raise ApplicationError(
            "Title must be at least 3 characters long.",
            code="title_too_short",
            status_code=400,
        )

    content_text = extract_plain_text(content_markdown)
    excerpt = generate_excerpt(content_text, max_length=300)

    # Slug generation with bounded retries for collision avoidance
    max_retries = 3
    for attempt in range(max_retries):
        slug = generate_post_slug(title)
        try:
            with transaction.atomic():
                post = Post.objects.create(
                    author=author,
                    category=category,
                    title=title,
                    slug=slug,
                    excerpt=excerpt,
                    content_markdown=content_markdown,
                    content_text=content_text,
                    status=Post.Status.DRAFT,
                    published_at=None,
                    like_count=0,
                )
                Post.objects.filter(pk=post.pk).update(
                    search_vector=(
                        SearchVector("title", weight="A", config="english")
                        + SearchVector("content_text", weight="B", config="english")
                    )
                )
                post.refresh_from_db(fields=["search_vector"])
                return post
        except IntegrityError as exc:
            if "uq_post_slug" in str(exc) or "slug" in str(exc):
                if attempt == max_retries - 1:
                    logger.error("Failed to generate unique slug after %d attempts", max_retries)
                    raise ApplicationError(
                        "Could not generate a unique slug. Please try again.",
                        code="slug_collision",
                        status_code=409,
                    ) from exc
                continue
            raise

    raise ApplicationError("Could not create post.", code="post_creation_failed")


def update_post(
    post: Post,
    author: Any,
    title: str | None = None,
    category: Category | None = None,
    content_markdown: str | None = None,
) -> Post:
    """
    Updates post title, category, or content. Slug and status are immutable here.
    Recomputes plain text, excerpt, and search vector when content or title changes.
    """
    if post.author_id != author.id:
        raise PermissionDenied("You do not have permission to edit this post.")

    update_fields = ["updated_at"]
    recompute_derived = False

    if title is not None:
        title = title.strip()
        if len(title) < 3:
            raise ApplicationError(
                "Title must be at least 3 characters long.",
                code="title_too_short",
                status_code=400,
            )
        post.title = title
        update_fields.append("title")
        recompute_derived = True

    if category is not None:
        post.category = category
        update_fields.append("category")

    if content_markdown is not None:
        post.content_markdown = content_markdown
        update_fields.append("content_markdown")
        recompute_derived = True

    if recompute_derived:
        post.content_text = extract_plain_text(post.content_markdown)
        post.excerpt = generate_excerpt(post.content_text, max_length=300)
        update_fields.extend(["content_text", "excerpt"])

    with transaction.atomic():
        post.save(update_fields=update_fields)
        if recompute_derived:
            Post.objects.filter(pk=post.pk).update(
                search_vector=(
                    SearchVector("title", weight="A", config="english")
                    + SearchVector("content_text", weight="B", config="english")
                )
            )
            post.refresh_from_db(fields=["search_vector"])

    return post


def publish_post(post: Post, author: Any) -> Post:
    """
    Transitions a post from draft to published.
    Preconditions: owner must have a verified email, non-blank content, and category set.
    Idempotent: publishing an already published post returns 200 without changes.
    published_at is recorded once and never overwritten on subsequent publish calls.
    """
    if post.author_id != author.id:
        raise PermissionDenied("You do not have permission to publish this post.")

    if not author.is_email_verified:
        raise EmailNotVerifiedError("You must verify your email address before publishing a post.")

    if not post.content_markdown or not post.content_markdown.strip():
        raise ApplicationError(
            "Cannot publish a post with blank content.",
            code="blank_content",
            status_code=400,
        )

    # Idempotent return if already published
    if post.status == Post.Status.PUBLISHED:
        return post

    now = timezone.now()
    post.status = Post.Status.PUBLISHED
    if post.published_at is None:
        post.published_at = now

    with transaction.atomic():
        post.save(update_fields=["status", "published_at", "updated_at"])
        Post.objects.filter(pk=post.pk).update(
            search_vector=(
                SearchVector("title", weight="A", config="english")
                + SearchVector("content_text", weight="B", config="english")
            )
        )
        post.refresh_from_db(fields=["search_vector"])

    return post


def unpublish_post(post: Post, author: Any) -> Post:
    """
    Transitions a post from published back to draft.
    Preserves published_at for historical first-publication timestamp.
    Idempotent: unpublishing a draft returns 200 without changes.
    """
    if post.author_id != author.id:
        raise PermissionDenied("You do not have permission to unpublish this post.")

    if post.status == Post.Status.DRAFT:
        return post

    post.status = Post.Status.DRAFT
    post.save(update_fields=["status", "updated_at"])
    return post


def delete_post(post: Post, author: Any) -> None:
    """
    Permanently deletes a post and cascades to comments, likes, and bookmarks.
    """
    if post.author_id != author.id:
        raise PermissionDenied("You do not have permission to delete this post.")

    post.delete()


def adjust_post_like_count(post_id: int, delta: int) -> None:
    """
    Atomically updates the denormalized like counter.
    Enforces non-negative count via database check constraint.
    """
    Post.objects.filter(id=post_id).update(like_count=models.F("like_count") + delta)
