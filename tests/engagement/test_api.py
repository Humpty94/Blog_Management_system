import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from blog.models import Category
from blog.services import create_post, publish_post, unpublish_post
from engagement.services import bookmark_post

User = get_user_model()


@pytest.fixture
def author():
    user = User.objects.create_user(
        email="api_eng_author@example.com",
        username="api_eng_author",
        password="Password123!",
    )
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at"])
    return user


@pytest.fixture
def reader():
    return User.objects.create_user(
        email="api_eng_reader@example.com",
        username="api_eng_reader",
        password="Password123!",
    )


@pytest.fixture
def published_post(author):
    category = Category.objects.create(name="Engagement API", slug="eng-api")
    post = create_post(
        author=author,
        category=category,
        title="Post For Engagement API Testing",
        content_markdown="Post body content.",
    )
    return publish_post(post, author)


@pytest.mark.django_db
def test_like_and_unlike_api(author, reader, published_post):
    client = APIClient()

    # 1. Unauthenticated like fails
    res_unauth = client.post(f"/api/v1/posts/{published_post.slug}/like/")
    assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Author liking own post fails with 400
    client.force_authenticate(user=author)
    res_self = client.post(f"/api/v1/posts/{published_post.slug}/like/")
    assert res_self.status_code == status.HTTP_400_BAD_REQUEST
    assert res_self.data["error"]["code"] == "self_like_prohibited"

    # 3. Reader likes post -> 200
    client.force_authenticate(user=reader)
    res_like = client.post(f"/api/v1/posts/{published_post.slug}/like/")
    assert res_like.status_code == status.HTTP_200_OK
    assert res_like.data["liked"] is True
    assert res_like.data["like_count"] == 1

    # 4. Reader likes again (idempotent) -> 200
    res_re_like = client.post(f"/api/v1/posts/{published_post.slug}/like/")
    assert res_re_like.status_code == status.HTTP_200_OK
    assert res_re_like.data["liked"] is True
    assert res_re_like.data["like_count"] == 1

    # 5. Reader unlikes post -> 200
    res_unlike = client.delete(f"/api/v1/posts/{published_post.slug}/like/")
    assert res_unlike.status_code == status.HTTP_200_OK
    assert res_unlike.data["liked"] is False
    assert res_unlike.data["like_count"] == 0

    # 6. Reader unlikes again (idempotent) -> 200
    res_re_unlike = client.delete(f"/api/v1/posts/{published_post.slug}/like/")
    assert res_re_unlike.status_code == status.HTTP_200_OK
    assert res_re_unlike.data["liked"] is False
    assert res_re_unlike.data["like_count"] == 0


@pytest.mark.django_db
def test_bookmark_api_and_user_bookmarks_listing(author, reader, published_post):
    client = APIClient()

    # 1. Unauthenticated bookmark fails
    res_unauth = client.post(f"/api/v1/posts/{published_post.slug}/bookmark/")
    assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Reader bookmarks post -> 200
    client.force_authenticate(user=reader)
    res_bm = client.post(f"/api/v1/posts/{published_post.slug}/bookmark/")
    assert res_bm.status_code == status.HTTP_200_OK
    assert res_bm.data["bookmarked"] is True

    # 3. Reader bookmarks again (idempotent) -> 200
    res_re_bm = client.post(f"/api/v1/posts/{published_post.slug}/bookmark/")
    assert res_re_bm.status_code == status.HTTP_200_OK
    assert res_re_bm.data["bookmarked"] is True

    # 4. List current user's bookmarks
    res_list = client.get("/api/v1/users/me/bookmarks/")
    assert res_list.status_code == status.HTTP_200_OK
    assert res_list.data["pagination"]["count"] == 1
    item = res_list.data["results"][0]
    assert item["post"]["slug"] == published_post.slug
    assert item["post"]["title"] == published_post.title

    # 5. When post is unpublished, it is excluded from bookmark list
    unpublish_post(post=published_post, author=author)
    res_list_after_unpublish = client.get("/api/v1/users/me/bookmarks/")
    assert res_list_after_unpublish.data["pagination"]["count"] == 0

    # 6. Republish post and verify it reappears in bookmark list
    publish_post(post=published_post, author=author)
    res_list_repub = client.get("/api/v1/users/me/bookmarks/")
    assert res_list_repub.data["pagination"]["count"] == 1

    # 7. Unbookmark post -> 204
    res_unbm = client.delete(f"/api/v1/posts/{published_post.slug}/bookmark/")
    assert res_unbm.status_code == status.HTTP_204_NO_CONTENT

    # 8. Unbookmark again (idempotent) -> 204
    res_re_unbm = client.delete(f"/api/v1/posts/{published_post.slug}/bookmark/")
    assert res_re_unbm.status_code == status.HTTP_204_NO_CONTENT

    # 9. List is now empty
    res_list_empty = client.get("/api/v1/users/me/bookmarks/")
    assert res_list_empty.data["pagination"]["count"] == 0


@pytest.mark.django_db
def test_user_bookmarks_private_isolation(author, reader, published_post):
    # Reader bookmarks published post
    bookmark_post(post_slug_or_id=published_post.slug, user=reader)

    client = APIClient()

    # Author querying their own bookmarks sees 0
    client.force_authenticate(user=author)
    res_author = client.get("/api/v1/users/me/bookmarks/")
    assert res_author.status_code == status.HTTP_200_OK
    assert res_author.data["pagination"]["count"] == 0

    # Reader querying sees 1
    client.force_authenticate(user=reader)
    res_reader = client.get("/api/v1/users/me/bookmarks/")
    assert res_reader.status_code == status.HTTP_200_OK
    assert res_reader.data["pagination"]["count"] == 1
