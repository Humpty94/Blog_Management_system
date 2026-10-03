"""
End-to-End Platform Lifecycle Integration Test Suite.

Tests complete multi-actor journeys through:
1. Registration, email verification, and JWT session handling
2. Draft creation and strict draft privacy enforcement
3. Email verification publishing gate and markdown rendering pipeline
4. Public feed browsing, category filtering, and full-text search
5. Discussion engine: single-reply-level constraint and placeholder deletion
6. Engagement: self-like prohibition, idempotent likes/bookmarks, and private bookmarks
7. Refresh token rotation and reuse detection
8. Account deactivation: anonymization, draft purge, bookmark purge, like preservation
9. Post unpublishing and status transitions
10. Background like count reconciliation
"""

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APIClient

from blog.models import Category, Post
from comments.models import Comment
from engagement.models import Bookmark, Like

User = get_user_model()


@pytest.mark.django_db
def test_full_platform_lifecycle():
    client = APIClient()

    # =========================================================================
    # Step 1: User Registration & Verification Lifecycle
    # =========================================================================
    # 1.1 Register Author
    author_payload = {
        "email": "lifecycle_author@example.com",
        "username": "author_life",
        "password": "AuthorSecurePass123!",
        "display_name": "Author Life",
    }
    res_reg_author = client.post("/api/v1/auth/register/", author_payload)
    assert res_reg_author.status_code == status.HTTP_201_CREATED
    assert "user" in res_reg_author.data
    author_user = User.objects.get(email="lifecycle_author@example.com")
    assert author_user.profile.display_name == "Author Life"
    assert author_user.email_verified_at is None

    # 1.2 Register Reader
    reader_payload = {
        "email": "lifecycle_reader@example.com",
        "username": "reader_life",
        "password": "ReaderSecurePass123!",
        "display_name": "Reader Life",
    }
    res_reg_reader = client.post("/api/v1/auth/register/", reader_payload)
    assert res_reg_reader.status_code == status.HTTP_201_CREATED
    reader_user = User.objects.get(email="lifecycle_reader@example.com")

    # 1.3 Author attempts to access protected endpoint without credentials
    res_unauth = client.get("/api/v1/users/me/")
    assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED
    assert res_unauth.data["error"]["code"] == "not_authenticated"

    # 1.4 Author logs in before email verification -> succeeds, issues JWT
    res_login_author = client.post(
        "/api/v1/auth/login/",
        {"email": "lifecycle_author@example.com", "password": "AuthorSecurePass123!"},
    )
    assert res_login_author.status_code == status.HTTP_200_OK
    author_access = res_login_author.data["access"]

    # 1.5 Reader logs in before verification
    res_login_reader = client.post(
        "/api/v1/auth/login/",
        {"email": "lifecycle_reader@example.com", "password": "ReaderSecurePass123!"},
    )
    reader_access = res_login_reader.data["access"]
    reader_refresh = res_login_reader.data["refresh"]

    # 1.6 Verify emails using single-use verification tokens
    from accounts.services import create_email_verification_token

    raw_token_auth, _ = create_email_verification_token(author_user)
    res_verify_auth = client.post("/api/v1/auth/verify-email/", {"token": raw_token_auth})
    assert res_verify_auth.status_code == status.HTTP_200_OK
    author_user.refresh_from_db()
    assert author_user.email_verified_at is not None

    raw_token_read, _ = create_email_verification_token(reader_user)
    res_verify_read = client.post("/api/v1/auth/verify-email/", {"token": raw_token_read})
    assert res_verify_read.status_code == status.HTTP_200_OK
    reader_user.refresh_from_db()
    assert reader_user.email_verified_at is not None

    # =========================================================================
    # Step 2: Taxonomy Setup
    # =========================================================================
    category = Category.objects.create(
        name="Architecture & Systems",
        slug="architecture-systems",
        description="Software architecture and systems design",
    )

    # =========================================================================
    # Step 3: Draft Creation & Draft Privacy Invariant
    # =========================================================================
    # 3.1 Author creates a draft post
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {author_access}")
    draft_payload = {
        "title": "Scalable Monolithic Systems in Python",
        "category_slug": category.slug,
        "content_markdown": (
            "# Scaling Monoliths\n\nCarefully partitioned boundaries keep systems maintainable."
        ),
    }
    res_create_draft = client.post("/api/v1/posts/", draft_payload)
    assert res_create_draft.status_code == status.HTTP_201_CREATED
    post_slug = res_create_draft.data["slug"]
    assert res_create_draft.data["status"] == "draft"
    assert res_create_draft.data["published_at"] is None

    # 3.2 Author can view own draft
    res_author_get = client.get(f"/api/v1/posts/{post_slug}/")
    assert res_author_get.status_code == status.HTTP_200_OK
    assert res_author_get.data["title"] == "Scalable Monolithic Systems in Python"

    # 3.3 Author sees draft in `/api/v1/users/me/posts/`
    res_me_posts = client.get("/api/v1/users/me/posts/")
    assert res_me_posts.status_code == status.HTTP_200_OK
    assert res_me_posts.data["pagination"]["count"] == 1
    assert res_me_posts.data["results"][0]["slug"] == post_slug

    # 3.4 Draft Privacy: Reader tries to view draft -> 404 NOT FOUND
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {reader_access}")
    res_reader_draft_get = client.get(f"/api/v1/posts/{post_slug}/")
    assert res_reader_draft_get.status_code == status.HTTP_404_NOT_FOUND

    # 3.5 Draft Privacy: Anonymous user tries to view draft -> 404 NOT FOUND
    client.credentials()
    res_anon_draft_get = client.get(f"/api/v1/posts/{post_slug}/")
    assert res_anon_draft_get.status_code == status.HTTP_404_NOT_FOUND

    # 3.6 Draft Privacy: Draft not listed in public feed
    res_feed = client.get("/api/v1/posts/")
    assert res_feed.status_code == status.HTTP_200_OK
    assert res_feed.data["pagination"]["count"] == 0

    # 3.7 Draft Privacy: Draft not listed in author's public profile posts
    res_author_public_posts = client.get(f"/api/v1/users/{author_user.username}/posts/")
    assert res_author_public_posts.status_code == status.HTTP_200_OK
    assert res_author_public_posts.data["pagination"]["count"] == 0

    # 3.8 Draft Privacy: Reader cannot comment, like, or bookmark the draft
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {reader_access}")
    res_draft_comment = client.post(
        f"/api/v1/posts/{post_slug}/comments/",
        {"body": "Draft comment"},
    )
    assert res_draft_comment.status_code == status.HTTP_404_NOT_FOUND

    res_draft_like = client.post(f"/api/v1/posts/{post_slug}/like/")
    assert res_draft_like.status_code == status.HTTP_404_NOT_FOUND

    res_draft_bm = client.post(f"/api/v1/posts/{post_slug}/bookmark/")
    assert res_draft_bm.status_code == status.HTTP_404_NOT_FOUND

    # =========================================================================
    # Step 4: Post Publishing & Public Visibility
    # =========================================================================
    # 4.1 Author publishes post
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {author_access}")
    res_publish = client.post(f"/api/v1/posts/{post_slug}/publish/")
    assert res_publish.status_code == status.HTTP_200_OK
    assert res_publish.data["status"] == "published"
    assert res_publish.data["published_at"] is not None

    # 4.2 Reader can now view published post
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {reader_access}")
    res_pub_get = client.get(f"/api/v1/posts/{post_slug}/")
    assert res_pub_get.status_code == status.HTTP_200_OK
    assert "<h1>Scaling Monoliths</h1>" in res_pub_get.data["content_html"]
    assert "Carefully partitioned boundaries" in res_pub_get.data["excerpt"]

    # 4.3 Appears in public feed
    res_public_feed = client.get("/api/v1/posts/")
    assert res_public_feed.status_code == status.HTTP_200_OK
    assert res_public_feed.data["pagination"]["count"] == 1
    assert res_public_feed.data["results"][0]["slug"] == post_slug

    # 4.4 Appears in author's public profile post list
    res_author_pub = client.get(f"/api/v1/users/{author_user.username}/posts/")
    assert res_author_pub.status_code == status.HTTP_200_OK
    assert res_author_pub.data["pagination"]["count"] == 1

    # 4.5 Filter by category and search
    res_cat_filter = client.get(f"/api/v1/posts/?category={category.slug}")
    assert res_cat_filter.status_code == status.HTTP_200_OK
    assert res_cat_filter.data["pagination"]["count"] == 1

    res_search = client.get("/api/v1/posts/?search=Monolithic")
    assert res_search.status_code == status.HTTP_200_OK
    assert res_search.data["pagination"]["count"] == 1

    # =========================================================================
    # Step 5: Discussion Engine (Single-Reply-Level Rule & Placeholder Rule)
    # =========================================================================
    # 5.1 Reader creates root comment
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {reader_access}")
    res_c1 = client.post(
        f"/api/v1/posts/{post_slug}/comments/",
        {"body": "This is a great root comment on architecture."},
    )
    assert res_c1.status_code == status.HTTP_201_CREATED
    c1_id = res_c1.data["id"]

    # 5.2 Author replies to reader's comment (1-level reply)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {author_access}")
    res_c2 = client.post(
        f"/api/v1/posts/{post_slug}/comments/",
        {"parent_id": c1_id, "body": "Thank you, appreciate your feedback!"},
    )
    assert res_c2.status_code == status.HTTP_201_CREATED
    c2_id = res_c2.data["id"]

    # 5.3 One-reply-level rule: Reader attempts to reply to reply `c2` -> 400 Bad Request
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {reader_access}")
    res_nested_reply = client.post(
        f"/api/v1/posts/{post_slug}/comments/",
        {"parent_id": c2_id, "body": "Nested reply attempt"},
    )
    assert res_nested_reply.status_code == status.HTTP_400_BAD_REQUEST
    assert res_nested_reply.data["error"]["code"] == "nested_replies_not_allowed"

    # 5.4 Standalone comment deletion (hard delete)
    res_standalone = client.post(
        f"/api/v1/posts/{post_slug}/comments/",
        {"body": "Standalone comment with no replies."},
    )
    standalone_id = res_standalone.data["id"]
    res_del_standalone = client.delete(f"/api/v1/comments/{standalone_id}/")
    assert res_del_standalone.status_code == status.HTTP_204_NO_CONTENT
    assert not Comment.objects.filter(id=standalone_id).exists()

    # 5.5 Placeholder deletion: Reader deletes root comment `c1` that HAS reply `c2`
    res_del_c1 = client.delete(f"/api/v1/comments/{c1_id}/")
    assert res_del_c1.status_code == status.HTTP_204_NO_CONTENT

    # Verify placeholder in DB: `is_deleted=True`, `body=""`
    c1_db = Comment.objects.get(id=c1_id)
    assert c1_db.is_deleted is True
    assert c1_db.body == ""

    # Verify comment list via API: root shows placeholder text, author is None, reply intact
    res_comments_list = client.get(f"/api/v1/posts/{post_slug}/comments/")
    assert res_comments_list.status_code == status.HTTP_200_OK
    assert len(res_comments_list.data["results"]) == 1
    root_comment = res_comments_list.data["results"][0]
    assert root_comment["is_deleted"] is True
    assert root_comment["author"] is None
    assert root_comment["body"] == "[This comment has been deleted]"
    assert len(root_comment["replies"]) == 1
    assert root_comment["replies"][0]["id"] == c2_id

    # 5.6 Placeholder deletion is idempotent
    res_del_again = client.delete(f"/api/v1/comments/{c1_id}/")
    assert res_del_again.status_code == status.HTTP_204_NO_CONTENT

    # =========================================================================
    # Step 6: Engagement (Self-Like Prohibition, Likes, Private Bookmarks)
    # =========================================================================
    # 6.1 Author attempts self-like -> 400 Bad Request
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {author_access}")
    res_self_like = client.post(f"/api/v1/posts/{post_slug}/like/")
    assert res_self_like.status_code == status.HTTP_400_BAD_REQUEST
    assert res_self_like.data["error"]["code"] == "self_like_prohibited"

    # 6.2 Reader likes post -> 200 OK, like_count incremented
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {reader_access}")
    res_like = client.post(f"/api/v1/posts/{post_slug}/like/")
    assert res_like.status_code == status.HTTP_200_OK
    assert res_like.data["liked"] is True
    assert res_like.data["like_count"] == 1

    post_db = Post.objects.get(slug=post_slug)
    assert post_db.like_count == 1

    # 6.3 Like idempotency: second like returns liked=True, like_count=1
    res_like_dup = client.post(f"/api/v1/posts/{post_slug}/like/")
    assert res_like_dup.status_code == status.HTTP_200_OK
    assert res_like_dup.data["liked"] is True
    assert res_like_dup.data["like_count"] == 1
    assert Like.objects.filter(post=post_db).count() == 1

    # 6.4 Reader bookmarks post -> 200 OK
    res_bm = client.post(f"/api/v1/posts/{post_slug}/bookmark/")
    assert res_bm.status_code == status.HTTP_200_OK
    assert res_bm.data["bookmarked"] is True

    # 6.5 Bookmark idempotency
    res_bm_dup = client.post(f"/api/v1/posts/{post_slug}/bookmark/")
    assert res_bm_dup.status_code == status.HTTP_200_OK
    assert res_bm_dup.data["bookmarked"] is True
    assert Bookmark.objects.filter(post=post_db, user=reader_user).count() == 1

    # 6.6 Reader views own bookmarks
    res_reader_bms = client.get("/api/v1/users/me/bookmarks/")
    assert res_reader_bms.status_code == status.HTTP_200_OK
    assert res_reader_bms.data["pagination"]["count"] == 1
    assert res_reader_bms.data["results"][0]["post"]["slug"] == post_slug

    # 6.7 Private bookmarks invariant: Author views own bookmarks -> 0 items
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {author_access}")
    res_author_bms = client.get("/api/v1/users/me/bookmarks/")
    assert res_author_bms.status_code == status.HTTP_200_OK
    assert res_author_bms.data["pagination"]["count"] == 0

    # =========================================================================
    # Step 7: Token Rotation & Reuse Detection
    # =========================================================================
    # 7.1 Reader rotates refresh token
    res_refresh = client.post("/api/v1/auth/refresh/", {"refresh": reader_refresh})
    assert res_refresh.status_code == status.HTTP_200_OK
    new_reader_refresh = res_refresh.data["refresh"]
    assert new_reader_refresh != reader_refresh

    # 7.2 Reuse detection: Attacker or compromised client reuses old refresh token
    res_reuse = client.post("/api/v1/auth/refresh/", {"refresh": reader_refresh})
    assert res_reuse.status_code == status.HTTP_401_UNAUTHORIZED
    assert res_reuse.data["error"]["code"] in ("token_reuse_detected", "token_invalid")

    # Entire family revoked by reuse detection! Even new token is now revoked
    res_after_reuse = client.post("/api/v1/auth/refresh/", {"refresh": new_reader_refresh})
    assert res_after_reuse.status_code == status.HTTP_401_UNAUTHORIZED

    # Reader logs back in cleanly
    res_relogin = client.post(
        "/api/v1/auth/login/",
        {"email": "lifecycle_reader@example.com", "password": "ReaderSecurePass123!"},
    )
    assert res_relogin.status_code == status.HTTP_200_OK
    reader_access = res_relogin.data["access"]

    # =========================================================================
    # Step 8: Account Deactivation & Anonymization Lifecycle
    # =========================================================================
    # 8.1 Reader deactivates account with password confirmation
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {reader_access}")
    res_deact = client.post("/api/v1/users/me/deactivate/", {"password": "ReaderSecurePass123!"})
    assert res_deact.status_code == status.HTTP_200_OK

    reader_user.refresh_from_db()
    assert reader_user.is_active is False
    assert reader_user.is_deactivated is True
    assert reader_user.email == f"deleted-{reader_user.id}@deleted.invalid"
    assert reader_user.username == f"deleted-{reader_user.id}"
    assert reader_user.profile.display_name == ""
    assert not reader_user.has_usable_password()

    from blog.serializers import AuthorSummarySerializer

    assert AuthorSummarySerializer(reader_user).data["display_name"] == "Deleted user"

    # 8.2 Reader bookmarks are purged permanently
    assert Bookmark.objects.filter(user=reader_user).count() == 0

    # 8.3 Reader likes are PRESERVED so post like_count remains accurate
    assert Like.objects.filter(post=post_db, user=reader_user).exists()
    post_db.refresh_from_db()
    assert post_db.like_count == 1

    # 8.4 Reader cannot log in again
    res_dead_login = client.post(
        "/api/v1/auth/login/",
        {"email": "lifecycle_reader@example.com", "password": "ReaderSecurePass123!"},
    )
    assert res_dead_login.status_code == status.HTTP_401_UNAUTHORIZED

    # =========================================================================
    # Step 9: Post Unpublishing & Draft Lifecycle
    # =========================================================================
    # 9.1 Author unpublishes post
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {author_access}")
    pub_time_before = post_db.published_at
    res_unpub = client.post(f"/api/v1/posts/{post_slug}/unpublish/")
    assert res_unpub.status_code == status.HTTP_200_OK
    assert res_unpub.data["status"] == "draft"

    post_db.refresh_from_db()
    assert post_db.status == "draft"
    # published_at timestamp is preserved for history
    assert post_db.published_at == pub_time_before

    # 9.2 Disappears from public feed
    client.credentials()
    res_pub_feed_after = client.get("/api/v1/posts/")
    assert res_pub_feed_after.status_code == status.HTTP_200_OK
    assert res_pub_feed_after.data["pagination"]["count"] == 0

    # =========================================================================
    # Step 10: Like Count Reconciliation Management Command
    # =========================================================================
    out = StringIO()
    call_command("reconcile_like_counts", stdout=out)
    output = out.getvalue()
    assert "Like count reconciliation complete. Reconciled 0 post(s)." in output


@pytest.mark.django_db
def test_author_deactivation_draft_purge_and_published_post_preservation():
    """
    Verifies that when an author deactivates:
    - Their unpublished drafts are deleted
    - Their published posts are preserved with author anonymized ('Deleted user')
    """
    client = APIClient()

    # 1. Register & verify author
    from accounts.services import create_email_verification_token, register_user

    author, _ = register_user(
        email="author_purge@example.com",
        username="author_purge",
        password="PurgePassword123!",
        display_name="Purge Author",
    )
    raw_token, _ = create_email_verification_token(author)
    client.post("/api/v1/auth/verify-email/", {"token": raw_token})

    # Log in
    res_login = client.post(
        "/api/v1/auth/login/",
        {"email": "author_purge@example.com", "password": "PurgePassword123!"},
    )
    author_access = res_login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {author_access}")

    # 2. Create category, draft post, and published post
    Category.objects.create(name="DevOps", slug="devops")

    res_draft = client.post(
        "/api/v1/posts/",
        {
            "title": "Private In-Progress Draft",
            "category_slug": "devops",
            "content_markdown": "Secret draft content",
        },
    )
    assert res_draft.status_code == status.HTTP_201_CREATED
    draft_slug = res_draft.data["slug"]

    res_pub = client.post(
        "/api/v1/posts/",
        {
            "title": "Public Architecture Guide",
            "category_slug": "devops",
            "content_markdown": "Public content for everyone.",
        },
    )
    assert res_pub.status_code == status.HTTP_201_CREATED
    pub_slug = res_pub.data["slug"]
    res_publish = client.post(f"/api/v1/posts/{pub_slug}/publish/")
    assert res_publish.status_code == status.HTTP_200_OK

    # 3. Deactivate author account
    res_deact = client.post("/api/v1/users/me/deactivate/", {"password": "PurgePassword123!"})
    assert res_deact.status_code == status.HTTP_200_OK

    # 4. Invariants check:
    # Draft is permanently deleted from database
    assert not Post.objects.filter(slug=draft_slug).exists()

    # Published post is preserved in database
    pub_post = Post.objects.get(slug=pub_slug)
    assert pub_post.status == "published"
    assert pub_post.author.id == author.id
    assert pub_post.author.is_active is False
    assert pub_post.author.email == f"deleted-{author.id}@deleted.invalid"

    # Public viewer can still read the post, author shows as "Deleted user"
    client.credentials()
    res_get_pub = client.get(f"/api/v1/posts/{pub_slug}/")
    assert res_get_pub.status_code == status.HTTP_200_OK
    assert res_get_pub.data["author"]["display_name"] == "Deleted user"
