import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.services import deactivate_user
from blog.models import Category, Post
from blog.services import create_post, publish_post

User = get_user_model()


@pytest.mark.django_db
def test_deactivation_purges_drafts_and_preserves_published_posts():
    user = User.objects.create_user(
        email="author_deact@example.com",
        username="author_deact",
        password="ValidPassword123!",
    )
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at"])

    category = Category.objects.create(name="Science", slug="science")

    # Author creates one published post and one private draft
    published_post = create_post(
        author=user,
        category=category,
        title="Published Scientific Paper",
        content_markdown="Findings and methodology.",
    )
    publish_post(published_post, user)

    draft_post = create_post(
        author=user,
        category=category,
        title="Unfinished Hypothesis",
        content_markdown="Private unverified musings.",
    )

    assert Post.objects.filter(author=user, status=Post.Status.DRAFT).count() == 1
    assert Post.objects.filter(author=user, status=Post.Status.PUBLISHED).count() == 1

    # Deactivate the author's account
    deactivate_user(user=user, password="ValidPassword123!")

    # Invariants verification:
    # 1. Draft post was permanently deleted
    assert not Post.objects.filter(pk=draft_post.pk).exists()
    assert Post.objects.filter(author=user, status=Post.Status.DRAFT).count() == 0

    # 2. Published post was preserved
    assert Post.objects.filter(pk=published_post.pk).exists()
    published_post.refresh_from_db()
    assert published_post.status == Post.Status.PUBLISHED
    assert published_post.author.username == f"deleted-{user.id}"

    # 3. Public API presents anonymized author attribution
    client = APIClient()
    res = client.get(f"/api/v1/posts/{published_post.slug}/")
    assert res.status_code == status.HTTP_200_OK
    assert res.data["author"]["username"] == f"deleted-{user.id}"
    assert res.data["author"]["display_name"] == "Deleted user"
