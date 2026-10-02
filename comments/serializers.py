from typing import Any

from rest_framework import serializers

from blog.serializers import AuthorSummarySerializer
from comments.models import Comment


class ReplySerializer(serializers.ModelSerializer):
    author = AuthorSummarySerializer(read_only=True)

    class Meta:
        model = Comment
        fields = (
            "id",
            "author",
            "body",
            "created_at",
            "updated_at",
        )


class CommentTreeSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    replies = ReplySerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = (
            "id",
            "author",
            "body",
            "is_deleted",
            "deleted_at",
            "created_at",
            "updated_at",
            "replies",
        )

    def get_author(self, obj: Comment) -> dict[str, Any] | None:
        if obj.is_deleted:
            return None
        return AuthorSummarySerializer(obj.author).data

    def get_body(self, obj: Comment) -> str:
        if obj.is_deleted:
            return "[This comment has been deleted]"
        return obj.body


class CommentCreateSerializer(serializers.Serializer):
    body = serializers.CharField(min_length=1, max_length=2000)
    parent_id = serializers.IntegerField(required=False, allow_null=True, default=None)
