import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from blog.models import Category, Post
from blog.services import (
    adjust_post_like_count,
    create_post,
    delete_post,
    publish_post,
    unpublish_post,
    update_post,
)
from common.exceptions import ApplicationError, EmailNotVerifiedError

User = get_user_model()


@pytest.fixture
def author():
    return User.objects.create_user(
        email="author_lifecycle@example.com",
        username="author_lifecycle",
        password="Password123!",
    )


@pytest.fixture
def other_user():
    return User.objects.create_user(
        email="other@example.com",
        username="other_user",
        password="Password123!",
    )


@pytest.fixture
def category():
    return Category.objects.create(name="Engineering", slug="engineering")


@pytest.mark.django_db
def test_create_post(author, category):
    post = create_post(
        author=author,
        category=category,
        title="Scalable Microservices",
        content_markdown="# Heading\n\nDetailed content for the article.",
    )

    assert post.status == Post.Status.DRAFT
    assert post.published_at is None
    assert post.slug.startswith("scalable-microservices-")
    assert post.content_text == "Heading Detailed content for the article."
    assert post.excerpt == "Heading Detailed content for the article."
    assert post.search_vector is not None


@pytest.mark.django_db
def test_update_post_slug_immutability(author, other_user, category):
    post = create_post(
        author=author,
        category=category,
        title="Initial Title",
        content_markdown="Initial content",
    )
    original_slug = post.slug

    # Non-author cannot update
    with pytest.raises(PermissionDenied):
        update_post(post=post, author=other_user, title="Malicious Update")

    # Author updates title and content
    updated = update_post(
        post=post,
        author=author,
        title="Updated Title Completely Different",
        content_markdown="Updated markdown content with **bold** text.",
    )

    assert updated.title == "Updated Title Completely Different"
    assert updated.slug == original_slug  # Slug remains strictly immutable
    assert "Updated markdown content with bold text." in updated.content_text


@pytest.mark.django_db
def test_publishing_lifecycle_and_invariants(author, other_user, category):
    post = create_post(
        author=author,
        category=category,
        title="Publishing Invariant Test",
        content_markdown="Rich markdown content to be published.",
    )

    # 1. Non-author cannot publish
    with pytest.raises(PermissionDenied):
        publish_post(post=post, author=other_user)

    # 2. Unverified email publishing gate blocks publication
    assert not author.is_email_verified
    with pytest.raises(EmailNotVerifiedError):
        publish_post(post=post, author=author)

    # 3. Blank content gate blocks publication even if verified
    author.email_verified_at = timezone.now()
    author.save(update_fields=["email_verified_at"])

    blank_post = create_post(
        author=author,
        category=category,
        title="Empty Post Title",
        content_markdown="    ",
    )
    with pytest.raises(ApplicationError) as exc_info:
        publish_post(post=blank_post, author=author)
    assert exc_info.value.code == "blank_content"

    # 4. Successful publication
    published = publish_post(post=post, author=author)
    assert published.status == Post.Status.PUBLISHED
    assert published.published_at is not None
    original_published_at = published.published_at

    # 5. Idempotent re-publish does not alter published_at
    republished = publish_post(post=published, author=author)
    assert republished.published_at == original_published_at

    # 6. Unpublish returns post to draft, while PRESERVING published_at
    draft = unpublish_post(post=published, author=author)
    assert draft.status == Post.Status.DRAFT
    assert draft.published_at == original_published_at  # Preserved!

    # 7. Idempotent re-unpublish
    redrafted = unpublish_post(post=draft, author=author)
    assert redrafted.status == Post.Status.DRAFT

    # 8. Re-publishing preserves original first published_at
    republished_again = publish_post(post=redrafted, author=author)
    assert republished_again.status == Post.Status.PUBLISHED
    assert republished_again.published_at == original_published_at


@pytest.mark.django_db
def test_delete_post(author, other_user, category):
    post = create_post(
        author=author,
        category=category,
        title="Post To Be Deleted",
        content_markdown="Content",
    )

    # Non-author cannot delete
    with pytest.raises(PermissionDenied):
        delete_post(post=post, author=other_user)

    # Author deletes post
    delete_post(post=post, author=author)
    assert not Post.objects.filter(pk=post.pk).exists()


@pytest.mark.django_db
def test_adjust_post_like_count(author, category):
    post = create_post(
        author=author,
        category=category,
        title="Post For Likes",
        content_markdown="Content",
    )
    assert post.like_count == 0

    adjust_post_like_count(post_id=post.pk, delta=1)
    post.refresh_from_db()
    assert post.like_count == 1

    adjust_post_like_count(post_id=post.pk, delta=-1)
    post.refresh_from_db()
    assert post.like_count == 0
