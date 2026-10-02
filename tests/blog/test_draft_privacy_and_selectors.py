import pytest
from django.contrib.auth import get_user_model
from django.http import Http404
from django.utils import timezone

from blog.models import Category, Post
from blog.selectors import (
    get_post_by_slug_for_viewer,
    get_published_post_or_404,
    list_published_posts,
    list_user_posts,
)
from blog.services import create_post, publish_post

User = get_user_model()


@pytest.fixture
def author():
    user = User.objects.create_user(
        email="author_sel@example.com",
        username="author_sel",
        password="Password123!",
    )
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at"])
    return user


@pytest.fixture
def stranger():
    return User.objects.create_user(
        email="stranger@example.com",
        username="stranger",
        password="Password123!",
    )


@pytest.fixture
def category():
    return Category.objects.create(name="AI Systems", slug="ai-systems")


@pytest.mark.django_db
def test_draft_privacy_in_get_post_by_slug_for_viewer(author, stranger, category):
    draft_post = create_post(
        author=author,
        category=category,
        title="Secret Draft Post",
        content_markdown="Unpublished draft content.",
    )

    # 1. Author can view own draft
    assert get_post_by_slug_for_viewer(draft_post.slug, viewer=author).id == draft_post.id

    # 2. Stranger cannot view draft -> raises Http404
    with pytest.raises(Http404):
        get_post_by_slug_for_viewer(draft_post.slug, viewer=stranger)

    # 3. Anonymous viewer cannot view draft -> raises Http404
    with pytest.raises(Http404):
        get_post_by_slug_for_viewer(draft_post.slug, viewer=None)

    # 4. Once published, anyone can view
    publish_post(draft_post, author)
    assert get_post_by_slug_for_viewer(draft_post.slug, viewer=stranger).id == draft_post.id
    assert get_post_by_slug_for_viewer(draft_post.slug, viewer=None).id == draft_post.id


@pytest.mark.django_db
def test_get_published_post_or_404(author, category):
    draft = create_post(
        author=author,
        category=category,
        title="Draft Only",
        content_markdown="Draft content.",
    )

    with pytest.raises(Http404):
        get_published_post_or_404(draft.slug)

    with pytest.raises(Http404):
        get_published_post_or_404(draft.id)

    publish_post(draft, author)
    assert get_published_post_or_404(draft.slug).id == draft.id
    assert get_published_post_or_404(draft.id).id == draft.id


@pytest.mark.django_db
def test_list_published_posts_and_fts_search(author, category):
    cat_ml = Category.objects.create(name="Machine Learning", slug="ml")

    p1 = create_post(
        author=author,
        category=category,
        title="Architecting Django Microservices",
        content_markdown="A deep dive into distributed systems and Python performance.",
    )
    p2 = create_post(
        author=author,
        category=cat_ml,
        title="Neural Networks from Scratch",
        content_markdown="Building deep learning architectures using PyTorch and math.",
    )
    # Draft should never appear
    create_post(
        author=author,
        category=category,
        title="Unpublished Notes on Architecture",
        content_markdown="Private draft.",
    )

    publish_post(p1, author)
    publish_post(p2, author)

    # Public list contains both published posts, excludes draft
    all_published = list(list_published_posts())
    assert len(all_published) == 2
    published_ids = {p.id for p in all_published}
    assert p1.id in published_ids
    assert p2.id in published_ids

    # Category filter
    ml_posts = list(list_published_posts(category_slug="ml"))
    assert len(ml_posts) == 1
    assert ml_posts[0].id == p2.id

    # Author filter
    author_posts = list(list_published_posts(author_username="author_sel"))
    assert len(author_posts) == 2

    # Full-text search
    search_django = list(list_published_posts(search="microservices"))
    assert len(search_django) == 1
    assert search_django[0].id == p1.id

    search_pytorch = list(list_published_posts(search="pytorch"))
    assert len(search_pytorch) == 1
    assert search_pytorch[0].id == p2.id


@pytest.mark.django_db
def test_list_user_posts_visibility_rules(author, stranger, category):
    p_published = create_post(
        author=author,
        category=category,
        title="Public Guide",
        content_markdown="Public content.",
    )
    p_draft = create_post(
        author=author,
        category=category,
        title="Private Ideas",
        content_markdown="Draft content.",
    )
    publish_post(p_published, author)

    # 1. Author viewing own posts sees both draft and published
    author_view = list(list_user_posts(target_user=author, viewer=author))
    assert len(author_view) == 2

    author_drafts_only = list(
        list_user_posts(target_user=author, viewer=author, status=Post.Status.DRAFT)
    )
    assert len(author_drafts_only) == 1
    assert author_drafts_only[0].id == p_draft.id

    # 2. Stranger viewing author's posts sees ONLY published post
    stranger_view = list(list_user_posts(target_user=author, viewer=stranger))
    assert len(stranger_view) == 1
    assert stranger_view[0].id == p_published.id

    # 3. Anonymous viewing author's posts sees ONLY published post
    anon_view = list(list_user_posts(target_user=author, viewer=None))
    assert len(anon_view) == 1
    assert anon_view[0].id == p_published.id
