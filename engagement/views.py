from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardPageNumberPagination
from common.throttles import WriteRateThrottle
from engagement.selectors import list_user_bookmarks
from engagement.serializers import (
    BookmarkItemSerializer,
    BookmarkStatusSerializer,
    LikeStatusSerializer,
)
from engagement.services import (
    bookmark_post,
    like_post,
    unbookmark_post,
    unlike_post,
)


class PostLikeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [WriteRateThrottle]

    @extend_schema(
        summary="Like a published post",
        tags=["Engagement"],
        request=None,
        responses={
            200: LikeStatusSerializer,
            400: OpenApiResponse(description="Self-like prohibited or invalid post"),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Published post not found"),
        },
    )
    def post(self, request, slug: str):
        post, _ = like_post(post_slug_or_id=slug, user=request.user)
        return Response(
            {"liked": True, "like_count": post.like_count},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Unlike a published post",
        tags=["Engagement"],
        request=None,
        responses={
            200: LikeStatusSerializer,
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Published post not found"),
        },
    )
    def delete(self, request, slug: str):
        post, _ = unlike_post(post_slug_or_id=slug, user=request.user)
        return Response(
            {"liked": False, "like_count": post.like_count},
            status=status.HTTP_200_OK,
        )


class PostBookmarkView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [WriteRateThrottle]

    @extend_schema(
        summary="Bookmark a published post",
        tags=["Engagement"],
        request=None,
        responses={
            200: BookmarkStatusSerializer,
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Published post not found"),
        },
    )
    def post(self, request, slug: str):
        bookmark_post(post_slug_or_id=slug, user=request.user)
        return Response(
            {"bookmarked": True},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Remove bookmark from a published post",
        tags=["Engagement"],
        request=None,
        responses={
            204: OpenApiResponse(description="Bookmark removed"),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Published post not found"),
        },
    )
    def delete(self, request, slug: str):
        unbookmark_post(post_slug_or_id=slug, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserBookmarksView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List current user's private bookmarked posts",
        tags=["Engagement"],
        parameters=[
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(name="page_size", type=int, required=False),
        ],
        responses={
            200: BookmarkItemSerializer(many=True),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        queryset = list_user_bookmarks(user=request.user)
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = BookmarkItemSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
