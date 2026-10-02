from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.selectors import get_active_profile_by_username, get_profile_by_user
from accounts.serializers import (
    CurrentUserProfileSerializer,
    DeactivateAccountSerializer,
    ProfileUpdateSerializer,
    PublicUserProfileSerializer,
    ResendVerificationEmailSerializer,
    TokenRefreshInputSerializer,
    TokenResponseSerializer,
    UserLoginSerializer,
    UserRegistrationSerializer,
    VerifyEmailSerializer,
)
from accounts.services import (
    deactivate_user,
    login_user,
    logout_user,
    register_user,
    resend_verification_email,
    rotate_refresh_token,
    verify_email,
)
from common.exceptions import NotFoundError
from common.throttles import AuthRateThrottle


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        summary="Register new user account",
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(description="User registered successfully"),
            400: OpenApiResponse(description="Validation error"),
            409: OpenApiResponse(description="Email or username already exists"),
        },
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, _ = register_user(**serializer.validated_data)
        return Response(
            {
                "message": "Registration successful. Please verify your email address.",
                "user": {
                    "username": user.username,
                    "email": user.email,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        summary="Verify user email address",
        request=VerifyEmailSerializer,
        responses={
            200: OpenApiResponse(description="Email verified successfully"),
            400: OpenApiResponse(description="Invalid or expired token"),
        },
    )
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verify_email(raw_token=serializer.validated_data["token"])
        return Response(
            {"message": "Email address verified successfully."},
            status=status.HTTP_200_OK,
        )


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        summary="Resend verification email",
        request=ResendVerificationEmailSerializer,
        responses={
            200: OpenApiResponse(description="Verification email dispatched if account exists"),
        },
    )
    def post(self, request):
        serializer = ResendVerificationEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resend_verification_email(email=serializer.validated_data["email"])
        return Response(
            {
                "message": (
                    "If an unverified account with this email address exists, "
                    "a verification link has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        summary="Authenticate user and issue JWT session",
        request=UserLoginSerializer,
        responses={
            200: TokenResponseSerializer,
            401: OpenApiResponse(description="Invalid credentials"),
        },
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        access_token, refresh_token, _ = login_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            user_agent=user_agent,
        )
        return Response(
            {
                "access": access_token,
                "refresh": refresh_token,
            },
            status=status.HTTP_200_OK,
        )


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        summary="Rotate refresh token and issue new token pair",
        request=TokenRefreshInputSerializer,
        responses={
            200: TokenResponseSerializer,
            401: OpenApiResponse(description="Invalid, expired, or reused token"),
        },
    )
    def post(self, request):
        serializer = TokenRefreshInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        access_token, refresh_token = rotate_refresh_token(
            refresh_token_str=serializer.validated_data["refresh"],
            user_agent=user_agent,
        )
        return Response(
            {
                "access": access_token,
                "refresh": refresh_token,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        summary="Log out and revoke active refresh token",
        request=TokenRefreshInputSerializer,
        responses={
            200: OpenApiResponse(description="Logged out successfully"),
        },
    )
    def post(self, request):
        serializer = TokenRefreshInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logout_user(refresh_token_str=serializer.validated_data["refresh"])
        return Response(
            {"message": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )


class CurrentUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get current user profile",
        responses={200: CurrentUserProfileSerializer},
    )
    def get(self, request):
        profile = get_profile_by_user(request.user)
        if not profile:
            raise NotFoundError("Profile not found.")
        serializer = CurrentUserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update current user profile",
        request=ProfileUpdateSerializer,
        responses={200: CurrentUserProfileSerializer},
    )
    def patch(self, request):
        profile = get_profile_by_user(request.user)
        if not profile:
            raise NotFoundError("Profile not found.")
        serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response_serializer = CurrentUserProfileSerializer(profile)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class DeactivateAccountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Deactivate and permanently anonymize current user account",
        request=DeactivateAccountSerializer,
        responses={
            200: OpenApiResponse(description="Account deactivated successfully"),
            400: OpenApiResponse(description="Invalid password confirmation"),
        },
    )
    def post(self, request):
        serializer = DeactivateAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deactivate_user(
            user=request.user,
            password=serializer.validated_data["password"],
        )
        return Response(
            {"message": "Account has been permanently deactivated and anonymized."},
            status=status.HTTP_200_OK,
        )


class PublicUserProfileView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(
        summary="Get public user profile by username",
        responses={
            200: PublicUserProfileSerializer,
            404: OpenApiResponse(description="User profile not found"),
        },
    )
    def get(self, request, username):
        profile = get_active_profile_by_username(username)
        if not profile:
            raise NotFoundError(
                f"User '@{username}' not found.",
                code="user_not_found",
            )
        serializer = PublicUserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)
