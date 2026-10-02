from typing import Any

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView


class IsAuthor(permissions.BasePermission):
    """
    Object-level permission allowing only the post author to modify it.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        return bool(
            request.user and request.user.is_authenticated and obj.author_id == request.user.id
        )
