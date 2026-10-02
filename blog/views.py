from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.selectors import get_user_by_username
from blog.permissions import IsAuthor
from blog.selectors import (
    get_category_by_slug,
    get_post_by_slug_for_viewer,
    list_categories,
    list_published_posts,
    list_user_posts,
)
from blog.serializers import (
    CategorySerializer,
    PostCreateSerializer,
    PostDetailSerializer,
    PostListSerializer,
    PostUpdateSerializer,
)
from blog.services import (
    create_post,
    delete_post,
    publish_post,
    unpublish_post,
    update_post,
)
from common.exceptions import NotFoundError
from common.pagination import StandardPageNumberPagination
from common.throttles import WriteRateThrottle


class CategoryListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="List all categories",
        tags=["Categories"],
        responses={200: CategorySerializer(many=True)},
    )
    def get(self, request):
        categories = list_categories()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)


class CategoryDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get category details by slug",
        tags=["Categories"],
        responses={
            200: CategorySerializer,
            404: OpenApiResponse(description="Category not found"),
        },
    )
    def get(self, request, slug: str):
        category = get_category_by_slug(slug)
        serializer = CategorySerializer(category)
        return Response(serializer.data)


class PostListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_throttles(self):
        if self.request.method == "POST":
            return [WriteRateThrottle()]
        return []

    @extend_schema(
        summary="Browse published posts with filtering and search",
        tags=["Posts"],
        parameters=[
            OpenApiParameter(
                name="category",
                type=str,
                description="Filter by category slug",
                required=False,
            ),
            OpenApiParameter(
                name="author",
                type=str,
                description="Filter by author username",
                required=False,
            ),
            OpenApiParameter(
                name="search",
                type=str,
                description="Full-text search query across title and content",
                required=False,
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                description="Sort by '-published_at' (default) or 'popular' / '-like_count'",
                required=False,
            ),
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(name="page_size", type=int, required=False),
        ],
        responses={200: PostListSerializer(many=True)},
    )
    def get(self, request):
        category_slug = request.query_params.get("category")
        author_username = request.query_params.get("author")
        search = request.query_params.get("search")
        ordering = request.query_params.get("ordering")

        queryset = list_published_posts(
            category_slug=category_slug,
            author_username=author_username,
            search=search,
            ordering=ordering,
        )

        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PostListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create a new draft post",
        tags=["Posts"],
        request=PostCreateSerializer,
        responses={
            201: PostDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Category not found"),
        },
    )
    def post(self, request):
        serializer = PostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        category = get_category_by_slug(serializer.validated_data["category_slug"])
        post = create_post(
            author=request.user,
            category=category,
            title=serializer.validated_data["title"],
            content_markdown=serializer.validated_data.get("content_markdown", ""),
        )
        output_serializer = PostDetailSerializer(post)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class PostDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ("PATCH", "DELETE"):
            return [IsAuthenticated(), IsAuthor()]
        return [AllowAny()]

    def get_throttles(self):
        if self.request.method in ("PATCH", "DELETE"):
            return [WriteRateThrottle()]
        return []

    @extend_schema(
        summary="Get post details by slug",
        tags=["Posts"],
        responses={
            200: PostDetailSerializer,
            404: OpenApiResponse(description="Post not found or private draft"),
        },
    )
    def get(self, request, slug: str):
        post = get_post_by_slug_for_viewer(slug, request.user)
        serializer = PostDetailSerializer(post)
        return Response(serializer.data)

    @extend_schema(
        summary="Update a post",
        tags=["Posts"],
        request=PostUpdateSerializer,
        responses={
            200: PostDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Forbidden - not the author"),
            404: OpenApiResponse(description="Post or category not found"),
        },
    )
    def patch(self, request, slug: str):
        post = get_post_by_slug_for_viewer(slug, request.user)
        self.check_object_permissions(request, post)

        serializer = PostUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        category = None
        if "category_slug" in serializer.validated_data:
            category = get_category_by_slug(serializer.validated_data["category_slug"])

        updated_post = update_post(
            post=post,
            author=request.user,
            title=serializer.validated_data.get("title"),
            category=category,
            content_markdown=serializer.validated_data.get("content_markdown"),
        )
        return Response(PostDetailSerializer(updated_post).data)

    @extend_schema(
        summary="Delete a post",
        tags=["Posts"],
        responses={
            204: OpenApiResponse(description="Post deleted successfully"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Forbidden - not the author"),
            404: OpenApiResponse(description="Post not found"),
        },
    )
    def delete(self, request, slug: str):
        post = get_post_by_slug_for_viewer(slug, request.user)
        self.check_object_permissions(request, post)

        delete_post(post=post, author=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostPublishView(APIView):
    permission_classes = [IsAuthenticated, IsAuthor]
    throttle_classes = [WriteRateThrottle]

    @extend_schema(
        summary="Publish a post",
        tags=["Posts"],
        request=None,
        responses={
            200: PostDetailSerializer,
            400: OpenApiResponse(description="Blank content or invalid state"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Email not verified or not the author"),
            404: OpenApiResponse(description="Post not found"),
        },
    )
    def post(self, request, slug: str):
        post = get_post_by_slug_for_viewer(slug, request.user)
        self.check_object_permissions(request, post)

        published_post = publish_post(post=post, author=request.user)
        return Response(PostDetailSerializer(published_post).data)


class PostUnpublishView(APIView):
    permission_classes = [IsAuthenticated, IsAuthor]
    throttle_classes = [WriteRateThrottle]

    @extend_schema(
        summary="Unpublish a post (return to draft)",
        tags=["Posts"],
        request=None,
        responses={
            200: PostDetailSerializer,
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not the author"),
            404: OpenApiResponse(description="Post not found"),
        },
    )
    def post(self, request, slug: str):
        post = get_post_by_slug_for_viewer(slug, request.user)
        self.check_object_permissions(request, post)

        draft_post = unpublish_post(post=post, author=request.user)
        return Response(PostDetailSerializer(draft_post).data)


class UserMePostsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List current user's posts (drafts and published)",
        tags=["Posts"],
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                description="Filter by 'draft' or 'published'",
                required=False,
            ),
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(name="page_size", type=int, required=False),
        ],
        responses={200: PostListSerializer(many=True)},
    )
    def get(self, request):
        post_status = request.query_params.get("status")
        queryset = list_user_posts(
            target_user=request.user,
            viewer=request.user,
            status=post_status,
        )
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PostListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class UserPublicPostsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="List public published posts by author username",
        tags=["Posts"],
        parameters=[
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(name="page_size", type=int, required=False),
        ],
        responses={
            200: PostListSerializer(many=True),
            404: OpenApiResponse(description="User not found"),
        },
    )
    def get(self, request, username: str):
        user = get_user_by_username(username)
        if not user or not user.is_active:
            raise NotFoundError("User not found.")

        queryset = list_user_posts(
            target_user=user,
            viewer=request.user,
        )
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PostListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
