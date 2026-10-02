from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from accounts.models import EmailVerificationToken, Profile, RefreshTokenRecord, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "id",
        "email",
        "username",
        "is_active",
        "is_staff",
        "email_verified_at",
        "deactivated_at",
        "date_joined",
    )
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email", "username")
    ordering = ("id",)
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Lifecycle Timestamps",
            {"fields": ("email_verified_at", "deactivated_at", "last_login", "date_joined")},
        ),
    )
    readonly_fields = ("date_joined", "last_login")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "created_at", "updated_at")
    search_fields = ("user__email", "user__username", "display_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "expires_at", "used_at")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("created_at", "token_hash")


@admin.register(RefreshTokenRecord)
class RefreshTokenRecordAdmin(admin.ModelAdmin):
    list_display = (
        "jti",
        "user",
        "family_id",
        "issued_at",
        "expires_at",
        "revoked_at",
        "revoke_reason",
    )
    list_filter = ("revoke_reason",)
    search_fields = ("user__email", "jti", "family_id")
    readonly_fields = ("issued_at", "jti", "family_id", "family_started_at")
