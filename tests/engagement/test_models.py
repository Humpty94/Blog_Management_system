import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.services import deactivate_user
from blog.models import Category
from blog.services import create_post, delete_post, publish_post
from engagement.models import Bookmark, Like

User = get_user_model()


@pytest.fixture
def author():
    user = User.objects.create_user(
        email="eng_author@example.com",
        username="eng_author",
        password="ValidPassword123!",
    )
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at"])
    return user


@pytest.fixture
def reader():
    return User.objects.create_user(
        email="eng_reader@example.com",
        username="eng_reader",
        password="ValidPassword123!",
    )


@pytest.fixture
def post(author):
    category = Category.objects.create(name="Engagement Cat", slug="eng-cat")
    p = create_post(
        author=author,
        category=category,
        title="Post For Engagement Model Tests",
        content_markdown="Content here.",
    )
    return publish_post(p, author)


@pytest.mark.django_db
def test_like_unique_constraint(reader, post):
    Like.objects.create(user=reader, post=post)

    # uq_like_user_post blocks duplicate like for same (user, post)
    with pytest.raises(IntegrityError), transaction.atomic():
        Like.objects.create(user=reader, post=post)


@pytest.mark.django_db
def test_bookmark_unique_constraint(reader, post):
    Bookmark.objects.create(user=reader, post=post)

    # uq_bookmark_user_post blocks duplicate bookmark for same (user, post)
    with pytest.raises(IntegrityError), transaction.atomic():
        Bookmark.objects.create(user=reader, post=post)


@pytest.mark.django_db
def test_post_cascade_deletion_removes_likes_and_bookmarks(author, reader, post):
    Like.objects.create(user=reader, post=post)
    Bookmark.objects.create(user=reader, post=post)

    assert Like.objects.filter(post=post).count() == 1
    assert Bookmark.objects.filter(post=post).count() == 1

    delete_post(post=post, author=author)

    assert Like.objects.filter(post_id=post.id).count() == 0
    assert Bookmark.objects.filter(post_id=post.id).count() == 0


@pytest.mark.django_db
def test_deactivation_preserves_likes_and_purges_bookmarks(author, reader, post):
    Like.objects.create(user=reader, post=post)
    Bookmark.objects.create(user=reader, post=post)

    # Reader deactivates account
    deactivate_user(user=reader, password="ValidPassword123!")

    # Invariants verification:
    # 1. Likes are PRESERVED so post like_count remains accurate
    assert Like.objects.filter(user=reader, post=post).exists()

    # 2. Bookmarks are PERMANENTLY DELETED (private data cleanup)
    assert not Bookmark.objects.filter(user=reader, post=post).exists()
