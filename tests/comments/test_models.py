import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.services import deactivate_user
from blog.models import Category, Post
from blog.services import create_post, delete_post, publish_post
from comments.models import Comment

User = get_user_model()


@pytest.fixture
def author():
    user = User.objects.create_user(
        email="comment_author@example.com",
        username="comment_author",
        password="ValidPassword123!",
    )
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at"])
    return user


@pytest.fixture
def post(author):
    category = Category.objects.create(name="Comments Category", slug="comments-cat")
    p = create_post(
        author=author,
        category=category,
        title="Post For Comments Testing",
        content_markdown="Content for testing comments.",
    )
    return publish_post(p, author)


@pytest.mark.django_db
def test_comment_check_constraint_not_self_parent(author, post):
    comment = Comment.objects.create(
        post=post,
        author=author,
        body="Initial body",
    )

    # Violating ck_comment_not_self_parent: setting parent_id = id
    comment.parent_id = comment.id
    with pytest.raises(IntegrityError), transaction.atomic():
        comment.save(update_fields=["parent"])


@pytest.mark.django_db
def test_comment_check_constraint_deleted_state(author, post):
    # is_deleted=True but deleted_at=None violates ck_comment_deleted_state
    with pytest.raises(IntegrityError), transaction.atomic():
        Comment.objects.create(
            post=post,
            author=author,
            body="Body",
            is_deleted=True,
            deleted_at=None,
        )

    # is_deleted=False but deleted_at is set violates ck_comment_deleted_state
    with pytest.raises(IntegrityError), transaction.atomic():
        Comment.objects.create(
            post=post,
            author=author,
            body="Body",
            is_deleted=False,
            deleted_at=timezone.now(),
        )


@pytest.mark.django_db
def test_comment_check_constraint_not_blank_unless_deleted(author, post):
    # Blank body when is_deleted=False violates ck_comment_not_blank_unless_deleted
    with pytest.raises(IntegrityError), transaction.atomic():
        Comment.objects.create(
            post=post,
            author=author,
            body="   ",
            is_deleted=False,
            deleted_at=None,
        )

    # Empty body allowed when is_deleted=True
    deleted_comment = Comment.objects.create(
        post=post,
        author=author,
        body="",
        is_deleted=True,
        deleted_at=timezone.now(),
    )
    assert deleted_comment.id is not None


@pytest.mark.django_db
def test_comment_check_constraint_body_length(author, post):
    # Body exceeding 2000 characters violates ck_comment_body_len
    with pytest.raises(IntegrityError), transaction.atomic():
        Comment.objects.create(
            post=post,
            author=author,
            body="a" * 2001,
            is_deleted=False,
            deleted_at=None,
        )


@pytest.mark.django_db
def test_post_cascade_deletion_removes_comments(author, post):
    c1 = Comment.objects.create(post=post, author=author, body="Root comment")
    Comment.objects.create(post=post, author=author, parent=c1, body="Reply comment")

    assert Comment.objects.filter(post=post).count() == 2

    # Hard-deleting the post cascades to all its comments and replies
    delete_post(post=post, author=author)

    assert Comment.objects.filter(post_id=post.id).count() == 0


@pytest.mark.django_db
def test_deactivating_user_preserves_comments(author, post):
    comment = Comment.objects.create(post=post, author=author, body="User comment to preserve")

    deactivate_user(user=author, password="ValidPassword123!")

    # Comment is preserved
    comment.refresh_from_db()
    assert comment.author.is_active is False
    assert comment.author.username == f"deleted-{author.id}"
    assert comment.body == "User comment to preserve"
