import pytest
from django.contrib.auth import get_user_model
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from blog.models import Category
from blog.services import create_post, publish_post
from comments.models import Comment
from comments.services import create_comment, delete_comment
from common.exceptions import ApplicationError

User = get_user_model()


@pytest.fixture
def author():
    user = User.objects.create_user(
        email="commenter1@example.com",
        username="commenter1",
        password="Password123!",
    )
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at"])
    return user


@pytest.fixture
def other_user():
    return User.objects.create_user(
        email="commenter2@example.com",
        username="commenter2",
        password="Password123!",
    )


@pytest.fixture
def published_post(author):
    category = Category.objects.create(name="Tech", slug="tech")
    post = create_post(
        author=author,
        category=category,
        title="Published Post For Discussion",
        content_markdown="Post body.",
    )
    return publish_post(post, author)


@pytest.fixture
def draft_post(author):
    category, _ = Category.objects.get_or_create(name="Tech", slug="tech")
    return create_post(
        author=author,
        category=category,
        title="Draft Post Secret",
        content_markdown="Draft body.",
    )


@pytest.mark.django_db
def test_create_root_and_reply_comment(author, other_user, published_post):
    root = create_comment(
        post_slug_or_id=published_post.slug,
        author=author,
        body="This is a root comment.",
    )
    assert root.parent_id is None
    assert root.is_root is True
    assert root.body == "This is a root comment."

    reply = create_comment(
        post_slug_or_id=published_post.slug,
        author=other_user,
        body="This is a reply to the root comment.",
        parent_id=root.id,
    )
    assert reply.parent_id == root.id
    assert reply.is_reply is True


@pytest.mark.django_db
def test_single_reply_level_invariant(author, published_post):
    root = create_comment(
        post_slug_or_id=published_post.slug,
        author=author,
        body="Root comment.",
    )
    reply = create_comment(
        post_slug_or_id=published_post.slug,
        author=author,
        body="Level 1 reply.",
        parent_id=root.id,
    )

    # Attempting to reply to a reply violates the single-reply-level rule
    with pytest.raises(ApplicationError) as exc_info:
        create_comment(
            post_slug_or_id=published_post.slug,
            author=author,
            body="Level 2 reply (forbidden).",
            parent_id=reply.id,
        )
    assert exc_info.value.code == "nested_replies_not_allowed"


@pytest.mark.django_db
def test_cross_post_reply_prevention(author, published_post):
    category = Category.objects.get(slug="tech")
    post_two = create_post(
        author=author,
        category=category,
        title="Another Post",
        content_markdown="Content 2.",
    )
    publish_post(post_two, author)

    root_post_one = create_comment(
        post_slug_or_id=published_post.slug,
        author=author,
        body="Root on post 1.",
    )

    # Attempting to reply to a parent on a different post
    with pytest.raises(ApplicationError) as exc_info:
        create_comment(
            post_slug_or_id=post_two.slug,
            author=author,
            body="Cross-post reply attempt.",
            parent_id=root_post_one.id,
        )
    assert exc_info.value.code == "cross_post_reply"


@pytest.mark.django_db
def test_cannot_reply_to_deleted_placeholder(author, other_user, published_post):
    root = create_comment(
        post_slug_or_id=published_post.slug,
        author=author,
        body="Root before deletion.",
    )
    create_comment(
        post_slug_or_id=published_post.slug,
        author=other_user,
        body="Reply keeping thread alive.",
        parent_id=root.id,
    )

    # Author deletes root, creating placeholder
    delete_comment(comment_id=root.id, user=author)
    root.refresh_from_db()
    assert root.is_deleted is True

    # Attempting to reply to deleted placeholder fails
    with pytest.raises(ApplicationError) as exc_info:
        create_comment(
            post_slug_or_id=published_post.slug,
            author=other_user,
            body="Attempt to reply to placeholder.",
            parent_id=root.id,
        )
    assert exc_info.value.code == "cannot_reply_to_deleted"


@pytest.mark.django_db
def test_cannot_comment_on_draft_post(author, draft_post):
    with pytest.raises(Http404):
        create_comment(
            post_slug_or_id=draft_post.slug,
            author=author,
            body="Trying to comment on draft.",
        )


@pytest.mark.django_db
def test_comment_deletion_semantics(author, other_user, published_post):
    # 1. Non-author cannot delete comment
    root = create_comment(
        post_slug_or_id=published_post.slug,
        author=author,
        body="Root by author.",
    )
    with pytest.raises(PermissionDenied):
        delete_comment(comment_id=root.id, user=other_user)

    # 2. Root without replies: hard delete
    delete_comment(comment_id=root.id, user=author)
    assert not Comment.objects.filter(pk=root.pk).exists()

    # 3. Reply: always hard delete
    root2 = create_comment(
        post_slug_or_id=published_post.slug,
        author=author,
        body="Second root.",
    )
    reply = create_comment(
        post_slug_or_id=published_post.slug,
        author=other_user,
        body="Reply by other user.",
        parent_id=root2.id,
    )
    delete_comment(comment_id=reply.id, user=other_user)
    assert not Comment.objects.filter(pk=reply.pk).exists()
    assert Comment.objects.filter(pk=root2.pk).exists()

    # 4. Root with replies: soft placeholder delete
    reply2 = create_comment(
        post_slug_or_id=published_post.slug,
        author=other_user,
        body="Another reply keeping thread alive.",
        parent_id=root2.id,
    )
    delete_comment(comment_id=root2.id, user=author)
    root2.refresh_from_db()
    assert root2.is_deleted is True
    assert root2.body == ""
    assert root2.deleted_at is not None
    # Reply is intact
    assert Comment.objects.filter(pk=reply2.pk).exists()

    # 5. Subsequent delete on placeholder is idempotent
    delete_comment(comment_id=root2.id, user=author)
    root2.refresh_from_db()
    assert root2.is_deleted is True
