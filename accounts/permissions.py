from rest_framework.permissions import BasePermission

from common.exceptions import EmailNotVerifiedError


class IsEmailVerified(BasePermission):
    """
    Permission check requiring the authenticated user to have a verified email address.
    """

    message = "Email address has not been verified."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if not request.user.is_email_verified:
            raise EmailNotVerifiedError()
        return True
