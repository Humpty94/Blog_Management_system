from django.urls import path

from blog.views import (
    CategoryDetailView,
    CategoryListView,
    PostDetailView,
    PostListCreateView,
    PostPublishView,
    PostUnpublishView,
    UserMePostsView,
    UserPublicPostsView,
)

categories_urlpatterns = [
    path("", CategoryListView.as_view(), name="category-list"),
    path("<slug:slug>/", CategoryDetailView.as_view(), name="category-detail"),
]

posts_urlpatterns = [
    path("", PostListCreateView.as_view(), name="post-list-create"),
    path("<slug:slug>/publish/", PostPublishView.as_view(), name="post-publish"),
    path("<slug:slug>/unpublish/", PostUnpublishView.as_view(), name="post-unpublish"),
    path("<slug:slug>/", PostDetailView.as_view(), name="post-detail"),
]

blog_users_urlpatterns = [
    path("me/posts/", UserMePostsView.as_view(), name="user-me-posts"),
    path("<str:username>/posts/", UserPublicPostsView.as_view(), name="user-public-posts"),
]

urlpatterns = posts_urlpatterns
