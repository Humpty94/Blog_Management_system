import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from blog.models import Category
from blog.services import create_post, publish_post
from comments.services import create_comment

User = get_user_model()


@pytest.fixture
def author():
    user = User.objects.create_user(
        email="api_commenter1@example.com",
        username="api_commenter1",
        password="Password123!",
    )
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at"])
    return user


@pytest.fixture
def commenter():
    return User.objects.create_user(
        email="api_commenter2@example.com",
        username="api_commenter2",
        password="Password123!",
    )


@pytest.fixture
def published_post(author):
    category = Category.objects.create(name="Web Dev", slug="web-dev")
    post = create_post(
        author=author,
        category=category,
        title="Web Development in 2026",
        content_markdown="Post content for API testing.",
    )
    return publish_post(post, author)


@pytest.mark.django_db
def test_post_comments_read_api(author, commenter, published_post):
    root1 = create_comment(
        post_slug_or_id=published_post.slug,
        author=author,
        body="First root comment.",
    )
    create_comment(
        post_slug_or_id=published_post.slug,
        author=commenter,
        body="Reply to first root.",
        parent_id=root1.id,
    )
    root2 = create_comment(
        post_slug_or_id=published_post.slug,
        author=commenter,
        body="Second root comment.",
    )

    client = APIClient()
    res = client.get(f"/api/v1/posts/{published_post.slug}/comments/")
    assert res.status_code == status.HTTP_200_OK

    results = res.data["results"]
    assert len(results) == 2
    # Roots are ordered oldest first
    assert results[0]["id"] == root1.id
    assert len(results[0]["replies"]) == 1
    assert results[0]["replies"][0]["body"] == "Reply to first root."
    assert results[1]["id"] == root2.id
    assert len(results[1]["replies"]) == 0


@pytest.mark.django_db
def test_create_comment_api(author, commenter, published_post):
    client = APIClient()

    # 1. Unauthenticated fails
    res_unauth = client.post(
        f"/api/v1/posts/{published_post.slug}/comments/",
        {"body": "Hello world!"},
    )
    assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Authenticated user creates root comment
    client.force_authenticate(user=commenter)
    res_root = client.post(
        f"/api/v1/posts/{published_post.slug}/comments/",
        {"body": "Awesome post!"},
    )
    assert res_root.status_code == status.HTTP_201_CREATED
    root_id = res_root.data["id"]
    assert res_root.data["body"] == "Awesome post!"
    assert res_root.data["author"]["username"] == commenter.username

    # 3. Authenticated user creates reply
    client.force_authenticate(user=author)
    res_reply = client.post(
        f"/api/v1/posts/{published_post.slug}/comments/",
        {"body": "Thank you for reading!", "parent_id": root_id},
    )
    assert res_reply.status_code == status.HTTP_201_CREATED
    reply_id = res_reply.data["id"]

    # 4. Attempting to reply to a reply fails with 400
    res_nested = client.post(
        f"/api/v1/posts/{published_post.slug}/comments/",
        {"body": "Nested reply attempt", "parent_id": reply_id},
    )
    assert res_nested.status_code == status.HTTP_400_BAD_REQUEST
    assert res_nested.data["error"]["code"] == "nested_replies_not_allowed"


@pytest.mark.django_db
def test_delete_comment_api(author, commenter, published_post):
    client = APIClient()

    root = create_comment(
        post_slug_or_id=published_post.slug,
        author=author,
        body="Root comment to delete.",
    )
    reply = create_comment(
        post_slug_or_id=published_post.slug,
        author=commenter,
        body="Reply to comment.",
        parent_id=root.id,
    )

    # 1. Non-author cannot delete comment
    client.force_authenticate(user=commenter)
    res_forbidden = client.delete(f"/api/v1/comments/{root.id}/")
    assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN

    # 2. Author deletes root that has replies -> 204 (placeholder set)
    client.force_authenticate(user=author)
    res_placeholder = client.delete(f"/api/v1/comments/{root.id}/")
    assert res_placeholder.status_code == status.HTTP_204_NO_CONTENT

    # Inspect placeholder in API
    res_tree = client.get(f"/api/v1/posts/{published_post.slug}/comments/")
    placeholder_data = res_tree.data["results"][0]
    assert placeholder_data["is_deleted"] is True
    assert placeholder_data["author"] is None
    assert placeholder_data["body"] == "[This comment has been deleted]"
    # Reply still present
    assert len(placeholder_data["replies"]) == 1
    assert placeholder_data["replies"][0]["id"] == reply.id

    # 3. Second delete on placeholder is idempotent -> 204
    res_idempotent = client.delete(f"/api/v1/comments/{root.id}/")
    assert res_idempotent.status_code == status.HTTP_204_NO_CONTENT

    # 4. Reply author deletes reply -> 204 (hard deleted)
    client.force_authenticate(user=commenter)
    res_delete_reply = client.delete(f"/api/v1/comments/{reply.id}/")
    assert res_delete_reply.status_code == status.HTTP_204_NO_CONTENT

    # Inspect tree again: reply is gone
    res_tree2 = client.get(f"/api/v1/posts/{published_post.slug}/comments/")
    assert len(res_tree2.data["results"][0]["replies"]) == 0
