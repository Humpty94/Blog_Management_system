from django.urls import path

from accounts.views import (
    CurrentUserProfileView,
    DeactivateAccountView,
    LoginView,
    LogoutView,
    PublicUserProfileView,
    RefreshTokenView,
    RegisterView,
    ResendVerificationView,
    VerifyEmailView,
)

auth_urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="auth-resend-verification"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
]

users_urlpatterns = [
    path("me/deactivate/", DeactivateAccountView.as_view(), name="user-me-deactivate"),
    path("me/", CurrentUserProfileView.as_view(), name="user-me-profile"),
    path("<str:username>/", PublicUserProfileView.as_view(), name="user-public-profile"),
]

urlpatterns = auth_urlpatterns
