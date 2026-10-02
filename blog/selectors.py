from typing import Any

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db import models
from django.db.models import QuerySet
from django.http import Http404

from blog.models import Category, Post


def get_published_post_or_404(post_id_or_slug: int | str) -> Post:
    """
    Retrieves a published post by ID or slug.
    Raises Http404 if the post does not exist or is in draft status.
    Exposed for comments and engagement apps.
    """
    if isinstance(post_id_or_slug, int):
        lookup = {"id": post_id_or_slug}
    elif str(post_id_or_slug).isdigit():
        lookup = {"id": int(post_id_or_slug)}
    else:
        lookup = {"slug": str(post_id_or_slug)}

    try:
        return Post.objects.select_related("author", "author__profile", "category").get(
            status=Post.Status.PUBLISHED,
            **lookup,
        )
    except Post.DoesNotExist:
        raise Http404("Published post not found.") from None


def get_post_by_slug_for_viewer(slug: str, viewer: Any | None) -> Post:
    """
    Retrieves a post by slug with viewer-based access control.
    Enforces draft privacy: draft posts return 404 to all viewers except the author.
    """
    try:
        post = Post.objects.select_related("author", "author__profile", "category").get(slug=slug)
    except Post.DoesNotExist:
        raise Http404("Post not found.") from None

    if post.is_draft:
        if not viewer or not viewer.is_authenticated or viewer.id != post.author_id:
            raise Http404("Post not found.")

    return post


def list_published_posts(
    *,
    category_slug: str | None = None,
    author_username: str | None = None,
    search: str | None = None,
    ordering: str | None = None,
) -> QuerySet[Post]:
    """
    Returns published posts filtered by category, author, or full-text search.
    Ordered by public feed index (-published_at, -id) or popular index (-like_count, -id).
    """
    qs = Post.objects.filter(status=Post.Status.PUBLISHED).select_related(
        "author",
        "author__profile",
        "category",
    )

    if category_slug:
        qs = qs.filter(category__slug=category_slug)

    if author_username:
        qs = qs.filter(author__username=author_username.strip().lower())

    if search and search.strip():
        search_query = SearchQuery(search.strip(), config="english")
        qs = (
            qs.annotate(rank=SearchRank(models.F("search_vector"), search_query))
            .filter(search_vector=search_query)
            .order_by("-rank", "-published_at", "-id")
        )
    else:
        if ordering in ("popular", "-like_count"):
            qs = qs.order_by("-like_count", "-id")
        else:
            qs = qs.order_by("-published_at", "-id")

    return qs


def list_user_posts(
    target_user: Any,
    viewer: Any | None,
    status: str | None = None,
) -> QuerySet[Post]:
    """
    Returns posts authored by target_user.
    If viewer is the target_user, allows viewing drafts.
    If viewer is not the target_user (or anonymous), returns only published posts.
    """
    is_owner = viewer and viewer.is_authenticated and viewer.id == target_user.id

    if is_owner:
        qs = Post.objects.filter(author=target_user)
        if status in (Post.Status.DRAFT, Post.Status.PUBLISHED):
            qs = qs.filter(status=status)
        return qs.select_related("author", "author__profile", "category").order_by(
            "-created_at",
            "-id",
        )

    # Public viewer: strictly published posts only
    return (
        Post.objects.filter(author=target_user, status=Post.Status.PUBLISHED)
        .select_related("author", "author__profile", "category")
        .order_by("-published_at", "-id")
    )


def list_categories() -> QuerySet[Category]:
    """Returns all categories ordered alphabetically by name."""
    return Category.objects.all().order_by("name")


def get_category_by_slug(slug: str) -> Category:
    """Returns category by slug or raises Http404."""
    try:
        return Category.objects.get(slug=slug)
    except Category.DoesNotExist:
        raise Http404("Category not found.") from None
