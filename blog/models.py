from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models.functions import Length, Lower, Trim
from django.db.models.lookups import GreaterThan, GreaterThanOrEqual

from common.models import TimestampedModel


class Category(TimestampedModel):
    """
    Admin-managed classification for posts.
    """

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        db_table = "blog_category"
        verbose_name = "category"
        verbose_name_plural = "categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="uq_category_name_lower",
            ),
            models.UniqueConstraint(
                fields=["slug"],
                name="uq_category_slug",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Post(TimestampedModel):
    """
    Blog article with Markdown content, plain-text extraction, FTS vector,
    and a two-state lifecycle (draft, published).
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    id = models.BigAutoField(primary_key=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="posts",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="posts",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    excerpt = models.CharField(max_length=300, blank=True, default="")
    content_markdown = models.TextField(blank=True, default="")
    content_text = models.TextField(blank=True, default="")
    search_vector = SearchVectorField(null=True, blank=True, editable=False)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    like_count = models.IntegerField(default=0)

    class Meta:
        db_table = "blog_post"
        verbose_name = "post"
        verbose_name_plural = "posts"
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                name="uq_post_slug",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["draft", "published"]),
                name="ck_post_status",
            ),
            models.CheckConstraint(
                condition=~models.Q(status="published") | models.Q(published_at__isnull=False),
                name="ck_post_published_has_timestamp",
            ),
            models.CheckConstraint(
                condition=~models.Q(status="published")
                | GreaterThan(Length(Trim("content_markdown")), 0),
                name="ck_post_published_not_blank",
            ),
            models.CheckConstraint(
                condition=models.Q(like_count__gte=0),
                name="ck_post_like_count_nonneg",
            ),
            models.CheckConstraint(
                condition=GreaterThanOrEqual(Length("title"), 3),
                name="ck_post_title_len",
            ),
        ]
        indexes = [
            models.Index(
                fields=["-published_at", "-id"],
                name="idx_post_public_feed",
                condition=models.Q(status="published"),
            ),
            models.Index(
                fields=["category", "-published_at", "-id"],
                name="idx_post_category_public",
                condition=models.Q(status="published"),
            ),
            models.Index(
                fields=["author", "status", "-created_at", "-id"],
                name="idx_post_author_status",
            ),
            models.Index(
                fields=["-like_count", "-id"],
                name="idx_post_popular_public",
                condition=models.Q(status="published"),
            ),
            GinIndex(
                fields=["search_vector"],
                name="idx_post_search_gin",
                condition=models.Q(status="published"),
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_published(self) -> bool:
        return self.status == self.Status.PUBLISHED

    @property
    def is_draft(self) -> bool:
        return self.status == self.Status.DRAFT
