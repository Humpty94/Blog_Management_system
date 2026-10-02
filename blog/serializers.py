from typing import Any

from rest_framework import serializers

from blog.content import render_markdown
from blog.models import Category, Post


class CategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "created_at", "updated_at")


class AuthorSummarySerializer(serializers.Serializer):
    username = serializers.CharField()
    display_name = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()

    def get_display_name(self, obj: Any) -> str:
        if getattr(obj, "is_deactivated", False):
            return "Deleted user"
        profile = getattr(obj, "profile", None)
        if profile and profile.display_name:
            return profile.display_name
        return obj.username

    def get_bio(self, obj: Any) -> str:
        if getattr(obj, "is_deactivated", False):
            return ""
        profile = getattr(obj, "profile", None)
        return profile.bio if profile else ""


class PostListSerializer(serializers.ModelSerializer):
    category = CategorySummarySerializer(read_only=True)
    author = AuthorSummarySerializer(read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "category",
            "author",
            "status",
            "published_at",
            "like_count",
            "created_at",
            "updated_at",
        )


class PostDetailSerializer(serializers.ModelSerializer):
    category = CategorySummarySerializer(read_only=True)
    author = AuthorSummarySerializer(read_only=True)
    content_html = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "content_markdown",
            "content_html",
            "category",
            "author",
            "status",
            "published_at",
            "like_count",
            "created_at",
            "updated_at",
        )

    def get_content_html(self, obj: Post) -> str:
        return render_markdown(obj.content_markdown)


class PostCreateSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=3, max_length=200)
    category_slug = serializers.SlugField(max_length=100)
    content_markdown = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=50000,
    )


class PostUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=3, max_length=200, required=False)
    category_slug = serializers.SlugField(max_length=100, required=False)
    content_markdown = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50000,
    )
