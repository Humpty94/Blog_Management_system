from django.urls import path

from engagement.views import PostBookmarkView, PostLikeView, UserBookmarksView

post_engagement_urlpatterns = [
    path("<slug:slug>/like/", PostLikeView.as_view(), name="post-like"),
    path("<slug:slug>/bookmark/", PostBookmarkView.as_view(), name="post-bookmark"),
]

engagement_users_urlpatterns = [
    path("me/bookmarks/", UserBookmarksView.as_view(), name="user-me-bookmarks"),
]

urlpatterns = post_engagement_urlpatterns
