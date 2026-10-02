from django.urls import path

from comments.views import CommentDetailView, PostCommentsView

post_comments_urlpatterns = [
    path("<slug:slug>/comments/", PostCommentsView.as_view(), name="post-comments"),
]

comments_urlpatterns = [
    path("<int:comment_id>/", CommentDetailView.as_view(), name="comment-detail"),
]

urlpatterns = comments_urlpatterns
