from django.db.models import Prefetch, QuerySet
from django.http import Http404

from blog.selectors import get_published_post_or_404
from comments.models import Comment


def list_root_comments_for_post(post_slug_or_id: str | int) -> QuerySet[Comment]:
    """
    Returns root comments for a published post, ordered oldest first,
    with all replies prefetched and ordered oldest first.
    Served by idx_comment_roots and idx_comment_replies.
    """
    post = get_published_post_or_404(post_slug_or_id)

    replies_prefetch = Prefetch(
        "replies",
        queryset=Comment.objects.select_related("author", "author__profile").order_by(
            "created_at",
            "id",
        ),
    )

    return (
        Comment.objects.filter(post=post, parent__isnull=True)
        .select_related("author", "author__profile")
        .prefetch_related(replies_prefetch)
        .order_by("created_at", "id")
    )


def get_comment_by_id_or_404(comment_id: int) -> Comment:
    """Returns a comment by ID or raises Http404."""
    try:
        return Comment.objects.select_related("author", "author__profile", "post").get(
            id=comment_id
        )
    except Comment.DoesNotExist:
        raise Http404("Comment not found.") from None
