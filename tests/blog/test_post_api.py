import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from blog.models import Category, Post
from blog.services import create_post, publish_post

User = get_user_model()


@pytest.fixture
def author():
    user = User.objects.create_user(
        email="api_author@example.com",
        username="api_author",
        password="Password123!",
    )
    return user


@pytest.fixture
def stranger():
    return User.objects.create_user(
        email="api_stranger@example.com",
        username="api_stranger",
        password="Password123!",
    )


@pytest.fixture
def category():
    return Category.objects.create(
        name="Backend",
        slug="backend",
        description="Backend engineering topics",
    )


@pytest.mark.django_db
def test_category_api(category):
    client = APIClient()

    # List categories
    res = client.get("/api/v1/categories/")
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data) == 1
    assert res.data[0]["slug"] == "backend"

    # Category detail
    res_detail = client.get("/api/v1/categories/backend/")
    assert res_detail.status_code == status.HTTP_200_OK
    assert res_detail.data["name"] == "Backend"

    # Non-existent category
    res_404 = client.get("/api/v1/categories/nonexistent/")
    assert res_404.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_post_creation_api(author, category):
    client = APIClient()

    # 1. Unauthenticated request fails
    res_unauth = client.post(
        "/api/v1/posts/",
        {"title": "My New Post", "category_slug": "backend", "content_markdown": "Content"},
    )
    assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Authenticated user can create a draft even with unverified email
    client.force_authenticate(user=author)
    res = client.post(
        "/api/v1/posts/",
        {
            "title": "My New Post",
            "category_slug": "backend",
            "content_markdown": "## Hello World\n\nDraft content here.",
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.data
    assert data["status"] == "draft"
    assert data["published_at"] is None
    assert data["slug"].startswith("my-new-post-")
    assert "<h2>Hello World</h2>" in data["content_html"]


@pytest.mark.django_db
def test_post_detail_privacy_api(author, stranger, category):
    client = APIClient()
    post = create_post(
        author=author,
        category=category,
        title="Privacy Test Post",
        content_markdown="Draft content.",
    )

    # 1. Stranger gets 404 for draft post
    client.force_authenticate(user=stranger)
    res_stranger = client.get(f"/api/v1/posts/{post.slug}/")
    assert res_stranger.status_code == status.HTTP_404_NOT_FOUND

    # 2. Anonymous gets 404 for draft post
    client.logout()
    res_anon = client.get(f"/api/v1/posts/{post.slug}/")
    assert res_anon.status_code == status.HTTP_404_NOT_FOUND

    # 3. Author gets 200 for draft post
    client.force_authenticate(user=author)
    res_author = client.get(f"/api/v1/posts/{post.slug}/")
    assert res_author.status_code == status.HTTP_200_OK
    assert res_author.data["id"] == post.id


@pytest.mark.django_db
def test_post_publish_and_unpublish_api(author, stranger, category):
    client = APIClient()
    post = create_post(
        author=author,
        category=category,
        title="Publish Lifecycle API",
        content_markdown="Content ready to be published.",
    )

    # 1. Author cannot publish without verified email -> 403 email_not_verified
    client.force_authenticate(user=author)
    res_unverified = client.post(f"/api/v1/posts/{post.slug}/publish/")
    assert res_unverified.status_code == status.HTTP_403_FORBIDDEN
    assert res_unverified.data["error"]["code"] == "email_not_verified"

    # 2. Verify author's email
    author.email_verified_at = timezone.now()
    author.save(update_fields=["email_verified_at"])

    # 3. Stranger cannot publish author's draft (draft privacy returns 404)
    client.force_authenticate(user=stranger)
    res_stranger = client.post(f"/api/v1/posts/{post.slug}/publish/")
    assert res_stranger.status_code == status.HTTP_404_NOT_FOUND

    # 4. Author publishes post -> 200
    client.force_authenticate(user=author)
    res_publish = client.post(f"/api/v1/posts/{post.slug}/publish/")
    assert res_publish.status_code == status.HTTP_200_OK
    assert res_publish.data["status"] == "published"
    assert res_publish.data["published_at"] is not None

    # 5. Stranger cannot unpublish published post -> 403 forbidden
    client.force_authenticate(user=stranger)
    res_unpublish_stranger = client.post(f"/api/v1/posts/{post.slug}/unpublish/")
    assert res_unpublish_stranger.status_code == status.HTTP_403_FORBIDDEN

    # 6. Author unpublishes post -> 200
    client.force_authenticate(user=author)
    res_unpublish = client.post(f"/api/v1/posts/{post.slug}/unpublish/")
    assert res_unpublish.status_code == status.HTTP_200_OK
    assert res_unpublish.data["status"] == "draft"


@pytest.mark.django_db
def test_post_update_api(author, stranger, category):
    client = APIClient()
    post = create_post(
        author=author,
        category=category,
        title="Original Title Here",
        content_markdown="Original content.",
    )
    original_slug = post.slug

    # 1. Author updates post
    client.force_authenticate(user=author)
    res = client.patch(
        f"/api/v1/posts/{post.slug}/",
        {"title": "Updated Title Here", "content_markdown": "Updated markdown."},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.data["title"] == "Updated Title Here"
    assert res.data["slug"] == original_slug  # Slug is immutable


@pytest.mark.django_db
def test_post_delete_api(author, category):
    client = APIClient()
    post = create_post(
        author=author,
        category=category,
        title="Post To Delete Via API",
        content_markdown="Content",
    )

    client.force_authenticate(user=author)
    res = client.delete(f"/api/v1/posts/{post.slug}/")
    assert res.status_code == status.HTTP_204_NO_CONTENT

    # Second delete returns 404
    res_second = client.delete(f"/api/v1/posts/{post.slug}/")
    assert res_second.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_user_posts_endpoints(author, stranger, category):
    author.email_verified_at = timezone.now()
    author.save(update_fields=["email_verified_at"])

    p_pub = create_post(author=author, category=category, title="Pub Post", content_markdown="C1")
    publish_post(p_pub, author)
    p_draft = create_post(author=author, category=category, title="Draft Post", content_markdown="C2")

    client = APIClient()

    # 1. GET /api/v1/users/me/posts/ authenticated as author
    client.force_authenticate(user=author)
    res_me = client.get("/api/v1/users/me/posts/")
    assert res_me.status_code == status.HTTP_200_OK
    assert res_me.data["pagination"]["count"] == 2

    # Filter own drafts
    res_me_drafts = client.get("/api/v1/users/me/posts/?status=draft")
    assert res_me_drafts.status_code == status.HTTP_200_OK
    assert res_me_drafts.data["pagination"]["count"] == 1
    assert res_me_drafts.data["results"][0]["slug"] == p_draft.slug

    # 2. GET /api/v1/users/<username>/posts/ as stranger
    client.force_authenticate(user=stranger)
    res_pub = client.get(f"/api/v1/users/{author.username}/posts/")
    assert res_pub.status_code == status.HTTP_200_OK
    assert res_pub.data["pagination"]["count"] == 1
    assert res_pub.data["results"][0]["slug"] == p_pub.slug
