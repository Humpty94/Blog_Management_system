from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import Profile
from accounts.validators import validate_username

User = get_user_model()


class UserRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    username = serializers.CharField(max_length=30, validators=[validate_username])
    password = serializers.CharField(write_only=True, validators=[validate_password])
    display_name = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default=""
    )
    bio = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TokenRefreshInputSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class ResendVerificationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class CurrentUserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    is_email_verified = serializers.BooleanField(source="user.is_email_verified", read_only=True)
    date_joined = serializers.DateTimeField(source="user.date_joined", read_only=True)

    class Meta:
        model = Profile
        fields = (
            "username",
            "email",
            "display_name",
            "bio",
            "is_email_verified",
            "date_joined",
        )


class PublicUserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    date_joined = serializers.DateTimeField(source="user.date_joined", read_only=True)

    class Meta:
        model = Profile
        fields = (
            "username",
            "display_name",
            "bio",
            "date_joined",
        )


class ProfileUpdateSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    bio = serializers.CharField(max_length=500, required=False, allow_blank=True)

    class Meta:
        model = Profile
        fields = ("display_name", "bio")


class DeactivateAccountSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
