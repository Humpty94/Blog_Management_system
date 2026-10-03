import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from common.middleware import get_current_request_id

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """
    Base domain exception for business rule violations raised in the service layer.
    """

    def __init__(
        self,
        message: str,
        code: str = "application_error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict | list | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class EmailNotVerifiedError(ApplicationError):
    def __init__(self, message: str = "Email address has not been verified."):
        super().__init__(
            message=message,
            code="email_not_verified",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ConflictError(ApplicationError):
    def __init__(self, message: str, code: str = "conflict", details: dict | None = None):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class NotFoundError(ApplicationError):
    def __init__(self, message: str, code: str = "not_found", details: dict | None = None):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


def custom_exception_handler(exc, context):
    """
    Unified exception handler converting all exceptions into a consistent error envelope:
    {
        "error": {
            "code": "...",
            "message": "...",
            "details": {...}
        },
        "request_id": "..."
    }
    """
    request = context.get("request")
    request_id = getattr(request, "id", None) or get_current_request_id() or "-"

    # Handle domain ApplicationErrors
    if isinstance(exc, ApplicationError):
        return Response(
            {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
                "request_id": request_id,
            },
            status=exc.status_code,
        )

    # Convert Django core exceptions to DRF exceptions
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    # Call DRF's default exception handler to get the standard response
    response = drf_exception_handler(exc, context)

    if response is not None:
        code = "error"
        message = "An error occurred."
        details = {}

        if isinstance(exc, exceptions.ValidationError):
            code = "validation_error"
            message = "Validation failed."
            details = response.data
        elif isinstance(exc, exceptions.NotAuthenticated):
            code = "not_authenticated"
            message = str(
                response.data.get("detail", "Authentication credentials were not provided.")
            )
        elif isinstance(exc, exceptions.AuthenticationFailed):
            detail_obj = response.data.get("detail")
            code_attr = getattr(detail_obj, "code", None) or getattr(exc, "code", None)
            raw_detail = str(detail_obj or "")
            if code_attr and code_attr != "authentication_failed":
                code = str(code_attr)
            elif "expired" in raw_detail.lower():
                code = "token_expired"
            elif "invalid" in raw_detail.lower():
                code = "token_invalid"
            else:
                code = "authentication_failed"
            message = raw_detail or "Authentication failed."
        elif isinstance(exc, exceptions.PermissionDenied):
            code = getattr(exc, "code", "permission_denied")
            message = str(
                response.data.get("detail", "You do not have permission to perform this action.")
            )
        elif isinstance(exc, exceptions.NotFound):
            code = "not_found"
            message = str(response.data.get("detail", "Resource not found."))
        elif isinstance(exc, exceptions.MethodNotAllowed):
            code = "method_not_allowed"
            message = str(response.data.get("detail", f"Method '{request.method}' not allowed."))
        elif isinstance(exc, exceptions.Throttled):
            code = "throttled"
            wait = exc.wait
            message = (
                f"Request was throttled. Expected available in {wait} seconds."
                if wait
                else "Request was throttled."
            )
            details = {"wait_seconds": wait}
        else:
            if isinstance(response.data, dict):
                message = str(response.data.get("detail", message))
                details = {k: v for k, v in response.data.items() if k != "detail"}
            else:
                details = response.data

        response.data = {
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
            "request_id": request_id,
        }
        return response

    # Unhandled 500 error
    logger.exception("Unhandled server error: %s", exc, extra={"request_id": request_id})
    return Response(
        {
            "error": {
                "code": "server_error",
                "message": "An unexpected server error occurred.",
                "details": {},
            },
            "request_id": request_id,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
