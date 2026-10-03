from rest_framework import serializers

from blog.serializers import PostListSerializer
from engagement.models import Bookmark


class LikeStatusSerializer(serializers.Serializer):
    liked = serializers.BooleanField()
    like_count = serializers.IntegerField()


class BookmarkStatusSerializer(serializers.Serializer):
    bookmarked = serializers.BooleanField()


class BookmarkItemSerializer(serializers.ModelSerializer):
    post = PostListSerializer(read_only=True)

    class Meta:
        model = Bookmark
        fields = ("id", "created_at", "post")
