from django.contrib import admin

from engagement.models import Bookmark, Like


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "post", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "post__title")
    readonly_fields = ("created_at",)
    raw_id_fields = ("user", "post")


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "post", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "post__title")
    readonly_fields = ("created_at",)
    raw_id_fields = ("user", "post")
