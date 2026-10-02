from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from comments.selectors import list_root_comments_for_post
from comments.serializers import (
    CommentCreateSerializer,
    CommentTreeSerializer,
    ReplySerializer,
)
from comments.services import create_comment, delete_comment
from common.pagination import StandardPageNumberPagination
from common.throttles import WriteRateThrottle


class PostCommentsView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_throttles(self):
        if self.request.method == "POST":
            return [WriteRateThrottle()]
        return []

    @extend_schema(
        summary="List comments for a post (roots with prefetched replies)",
        tags=["Comments"],
        parameters=[
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(name="page_size", type=int, required=False),
        ],
        responses={
            200: CommentTreeSerializer(many=True),
            404: OpenApiResponse(description="Published post not found"),
        },
    )
    def get(self, request, slug: str):
        queryset = list_root_comments_for_post(slug)
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = CommentTreeSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create a root comment or one-level reply on a published post",
        tags=["Comments"],
        request=CommentCreateSerializer,
        responses={
            201: CommentTreeSerializer,
            400: OpenApiResponse(description="Validation error or nested reply forbidden"),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Published post or parent not found"),
        },
    )
    def post(self, request, slug: str):
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = create_comment(
            post_slug_or_id=slug,
            author=request.user,
            body=serializer.validated_data["body"],
            parent_id=serializer.validated_data.get("parent_id"),
        )

        if comment.is_reply:
            output_serializer = ReplySerializer(comment)
        else:
            output_serializer = CommentTreeSerializer(comment)

        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class CommentDetailView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [WriteRateThrottle]

    @extend_schema(
        summary="Delete a comment (hard delete or placeholder for roots with replies)",
        tags=["Comments"],
        responses={
            204: OpenApiResponse(description="Comment deleted or placeholder set"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Forbidden - not the comment author"),
            404: OpenApiResponse(description="Comment not found"),
        },
    )
    def delete(self, request, comment_id: int):
        delete_comment(comment_id=comment_id, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
