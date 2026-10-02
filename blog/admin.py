from django import forms
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import render

from blog.models import Category, Post


class ReassignCategoryForm(forms.Form):
    target_category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=True,
        label="Target Category",
        help_text="All posts from selected categories will be reassigned to this category.",
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "post_count", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    actions = ["reassign_posts_action"]

    def post_count(self, obj: Category) -> int:
        return obj.posts.count()

    post_count.short_description = "Posts"

    @admin.action(description="Reassign posts to another category")
    def reassign_posts_action(self, request, queryset):
        selected_ids = list(queryset.values_list("id", flat=True))
        if "apply" in request.POST:
            form = ReassignCategoryForm(request.POST)
            if form.is_valid():
                target_category = form.cleaned_data["target_category"]
                updated_count = Post.objects.filter(category_id__in=selected_ids).update(
                    category=target_category
                )
                self.message_user(
                    request,
                    f"Successfully reassigned {updated_count} post(s) to '{target_category.name}'.",
                    messages.SUCCESS,
                )
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = ReassignCategoryForm()

        return render(
            request,
            "admin/reassign_category_intermediate.html",
            {
                "categories": queryset,
                "form": form,
                "title": "Reassign posts to another category",
            },
        )


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "author",
        "category",
        "status",
        "published_at",
        "like_count",
        "created_at",
    )
    list_filter = ("status", "category", "created_at")
    search_fields = ("title", "slug", "author__username")
    readonly_fields = (
        "slug",
        "published_at",
        "like_count",
        "excerpt",
        "content_text",
        "search_vector",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("author", "category")
