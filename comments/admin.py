from django.contrib import admin

from comments.models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "author", "parent", "is_deleted", "created_at")
    list_filter = ("is_deleted", "created_at")
    search_fields = ("author__username", "post__title", "body")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    raw_id_fields = ("post", "author", "parent")
