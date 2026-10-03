from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.http import Http404
from django.utils import timezone

from blog.models import Category, Post
from blog.services import create_post, publish_post
from common.exceptions import ApplicationError
from engagement.models import Bookmark, Like
from engagement.services import (
    bookmark_post,
    like_post,
    unbookmark_post,
    unlike_post,
)

User = get_user_model()


@pytest.fixture
def author():
    user = User.objects.create_user(
        email="svc_author@example.com",
        username="svc_author",
        password="Password123!",
    )
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at"])
    return user


@pytest.fixture
def reader():
    return User.objects.create_user(
        email="svc_reader@example.com",
        username="svc_reader",
        password="Password123!",
    )


@pytest.fixture
def published_post(author):
    category = Category.objects.create(name="Engagement Svc", slug="eng-svc")
    post = create_post(
        author=author,
        category=category,
        title="Post For Engagement Services",
        content_markdown="Post body.",
    )
    return publish_post(post, author)


@pytest.fixture
def draft_post(author):
    category, _ = Category.objects.get_or_create(name="Engagement Svc", slug="eng-svc")
    return create_post(
        author=author,
        category=category,
        title="Draft Post",
        content_markdown="Draft body.",
    )


@pytest.mark.django_db
def test_self_like_prohibition(author, published_post):
    # Author cannot like their own post
    with pytest.raises(ApplicationError) as exc_info:
        like_post(post_slug_or_id=published_post.slug, user=author)
    assert exc_info.value.code == "self_like_prohibited"


@pytest.mark.django_db
def test_like_and_unlike_lifecycle_and_idempotency(reader, published_post):
    assert published_post.like_count == 0

    # 1. First like increments counter
    post, created = like_post(post_slug_or_id=published_post.slug, user=reader)
    assert created is True
    assert post.like_count == 1
    assert Like.objects.filter(user=reader, post=published_post).count() == 1

    # 2. Second like (idempotent): does not increment counter
    post_re_liked, created_again = like_post(post_slug_or_id=published_post.slug, user=reader)
    assert created_again is False
    assert post_re_liked.like_count == 1
    assert Like.objects.filter(user=reader, post=published_post).count() == 1

    # 3. Unlike decrements counter
    post_unliked, deleted = unlike_post(post_slug_or_id=published_post.slug, user=reader)
    assert deleted is True
    assert post_unliked.like_count == 0
    assert Like.objects.filter(user=reader, post=published_post).count() == 0

    # 4. Second unlike (idempotent): counter does not decrement below zero
    post_unliked_again, deleted_again = unlike_post(
        post_slug_or_id=published_post.slug, user=reader
    )
    assert deleted_again is False
    assert post_unliked_again.like_count == 0


@pytest.mark.django_db
def test_cannot_like_draft_post(reader, draft_post):
    with pytest.raises(Http404):
        like_post(post_slug_or_id=draft_post.slug, user=reader)


@pytest.mark.django_db
def test_bookmark_lifecycle_and_author_self_bookmark(author, reader, published_post):
    # 1. Author bookmarking own published post is permitted
    bm_author, created_author = bookmark_post(post_slug_or_id=published_post.slug, user=author)
    assert created_author is True
    assert bm_author.user_id == author.id

    # 2. Reader bookmarks published post
    bm_reader, created_reader = bookmark_post(post_slug_or_id=published_post.slug, user=reader)
    assert created_reader is True
    assert Bookmark.objects.filter(user=reader, post=published_post).count() == 1

    # 3. Idempotent bookmark
    _, created_reader_again = bookmark_post(post_slug_or_id=published_post.slug, user=reader)
    assert created_reader_again is False

    # 4. Unbookmark removes bookmark
    assert unbookmark_post(post_slug_or_id=published_post.slug, user=reader) is True
    assert Bookmark.objects.filter(user=reader, post=published_post).count() == 0

    # 5. Idempotent unbookmark
    assert unbookmark_post(post_slug_or_id=published_post.slug, user=reader) is False


@pytest.mark.django_db
def test_cannot_bookmark_draft_post(reader, draft_post):
    with pytest.raises(Http404):
        bookmark_post(post_slug_or_id=draft_post.slug, user=reader)


@pytest.mark.django_db
def test_reconcile_like_counts_command(author, reader, published_post):
    # Reader likes post
    like_post(post_slug_or_id=published_post.slug, user=reader)
    published_post.refresh_from_db()
    assert published_post.like_count == 1

    # Manually introduce a counter discrepancy in the database
    Post.objects.filter(id=published_post.id).update(like_count=99)
    published_post.refresh_from_db()
    assert published_post.like_count == 99

    # Run reconciliation management command
    out = StringIO()
    call_command("reconcile_like_counts", stdout=out)
    output = out.getvalue()

    assert "Reconciled post" in output
    assert "99 -> 1" in output

    published_post.refresh_from_db()
    assert published_post.like_count == 1
