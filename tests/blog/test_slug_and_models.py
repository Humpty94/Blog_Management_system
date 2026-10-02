import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from blog.models import Category, Post
from blog.utils import generate_post_slug

User = get_user_model()


def test_generate_post_slug_latin():
    slug = generate_post_slug("Building a Great Blog Platform in Django")
    parts = slug.rsplit("-", 1)
    assert len(parts) == 2
    assert parts[0].startswith("building-a-great-blog-platform")
    assert len(parts[1]) == 8
    assert parts[1].isalnum()
    assert parts[1].islower()


def test_generate_post_slug_non_latin():
    slug = generate_post_slug("你好世界")  # Non-Latin characters produce empty slugify
    parts = slug.rsplit("-", 1)
    assert len(parts) == 2
    assert parts[0] == "post"
    assert len(parts[1]) == 8


@pytest.mark.django_db
def test_category_unique_constraints():
    Category.objects.create(name="Technology", slug="technology")

    # Lowercase uniqueness constraint fails
    with pytest.raises(IntegrityError), transaction.atomic():
        Category.objects.create(name="technology", slug="technology-2")

    # Slug uniqueness constraint fails
    with pytest.raises(IntegrityError), transaction.atomic():
        Category.objects.create(name="Tech", slug="technology")


@pytest.mark.django_db
def test_category_deletion_protection():
    author = User.objects.create_user(
        email="author@example.com",
        username="author",
        password="Password123!",
    )
    category = Category.objects.create(name="Design", slug="design")
    post = Post.objects.create(
        author=author,
        category=category,
        title="Design Principles",
        slug="design-principles-abc12345",
        content_markdown="Some content",
    )

    # Attempting to delete category protected by Post.category FK fails with ProtectedError
    with pytest.raises(models.ProtectedError):
        category.delete()

    # Reassigning post to another category permits deletion of original category
    target_category = Category.objects.create(name="Architecture", slug="architecture")
    post.category = target_category
    post.save(update_fields=["category"])

    category.delete()
    assert not Category.objects.filter(slug="design").exists()


@pytest.mark.django_db
def test_post_check_constraint_title_length():
    author = User.objects.create_user(
        email="author2@example.com",
        username="author2",
        password="Password123!",
    )
    category = Category.objects.create(name="Coding", slug="coding")

    # Title length < 3 fails ck_post_title_len
    with pytest.raises(IntegrityError):
        Post.objects.create(
            author=author,
            category=category,
            title="Hi",
            slug="hi-12345678",
            content_markdown="Content",
        )


@pytest.mark.django_db
def test_post_check_constraint_like_count_nonneg():
    author = User.objects.create_user(
        email="author3@example.com",
        username="author3",
        password="Password123!",
    )
    category = Category.objects.create(name="Python", slug="python")

    # Negative like_count fails ck_post_like_count_nonneg
    with pytest.raises(IntegrityError):
        Post.objects.create(
            author=author,
            category=category,
            title="Python Tips",
            slug="python-tips-12345678",
            content_markdown="Content",
            like_count=-1,
        )


@pytest.mark.django_db
def test_post_check_constraint_published_has_timestamp():
    author = User.objects.create_user(
        email="author4@example.com",
        username="author4",
        password="Password123!",
    )
    category = Category.objects.create(name="DevOps", slug="devops")

    # Status published with published_at=None fails ck_post_published_has_timestamp
    with pytest.raises(IntegrityError):
        Post.objects.create(
            author=author,
            category=category,
            title="Docker Basics",
            slug="docker-basics-12345678",
            content_markdown="Content",
            status=Post.Status.PUBLISHED,
            published_at=None,
        )


@pytest.mark.django_db
def test_post_check_constraint_published_not_blank():
    author = User.objects.create_user(
        email="author5@example.com",
        username="author5",
        password="Password123!",
    )
    category = Category.objects.create(name="Database", slug="database")

    # Status published with empty or whitespace-only content fails ck_post_published_not_blank
    with pytest.raises(IntegrityError):
        Post.objects.create(
            author=author,
            category=category,
            title="Postgres Indexing",
            slug="postgres-indexing-12345678",
            content_markdown="     ",
            status=Post.Status.PUBLISHED,
            published_at=timezone.now(),
        )
