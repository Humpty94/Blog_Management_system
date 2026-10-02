from rest_framework import exceptions, status
from rest_framework.test import APIRequestFactory

from common.exceptions import ApplicationError, ConflictError, custom_exception_handler


def test_custom_exception_handler_application_error():
    factory = APIRequestFactory()
    request = factory.get("/")
    request.id = "req-test-uuid-123"

    exc = ApplicationError(
        message="Post cannot be published without content.",
        code="post_content_empty",
        status_code=status.HTTP_400_BAD_REQUEST,
        details={"field": "content_markdown"},
    )
    context = {"request": request}

    response = custom_exception_handler(exc, context)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "error": {
            "code": "post_content_empty",
            "message": "Post cannot be published without content.",
            "details": {"field": "content_markdown"},
        },
        "request_id": "req-test-uuid-123",
    }


def test_custom_exception_handler_conflict_error():
    factory = APIRequestFactory()
    request = factory.get("/")
    request.id = "req-conflict-456"

    exc = ConflictError(
        message="Category name already exists.",
        code="category_conflict",
    )
    context = {"request": request}

    response = custom_exception_handler(exc, context)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["error"]["code"] == "category_conflict"
    assert response.data["request_id"] == "req-conflict-456"


def test_custom_exception_handler_validation_error():
    factory = APIRequestFactory()
    request = factory.post("/")
    request.id = "req-val-789"

    exc = exceptions.ValidationError({"email": ["Enter a valid email address."]})
    context = {"request": request}

    response = custom_exception_handler(exc, context)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error"]["code"] == "validation_error"
    assert "email" in response.data["error"]["details"]
    assert response.data["request_id"] == "req-val-789"


def test_custom_exception_handler_not_authenticated():
    factory = APIRequestFactory()
    request = factory.get("/")
    request.id = "req-auth-001"

    exc = exceptions.NotAuthenticated()
    context = {"request": request}

    response = custom_exception_handler(exc, context)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data["error"]["code"] == "not_authenticated"
    assert response.data["request_id"] == "req-auth-001"


def test_custom_exception_handler_token_errors():
    factory = APIRequestFactory()
    request = factory.get("/")
    request.id = "req-tok-001"

    exc_expired = exceptions.AuthenticationFailed("Token is expired")
    resp_exp = custom_exception_handler(exc_expired, {"request": request})
    assert resp_exp.data["error"]["code"] == "token_expired"

    exc_invalid = exceptions.AuthenticationFailed("Token is invalid")
    resp_inv = custom_exception_handler(exc_invalid, {"request": request})
    assert resp_inv.data["error"]["code"] == "token_invalid"


def test_custom_exception_handler_domain_errors():
    factory = APIRequestFactory()
    request = factory.get("/")
    request.id = "req-dom-001"

    from common.exceptions import EmailNotVerifiedError, NotFoundError

    resp_email = custom_exception_handler(EmailNotVerifiedError(), {"request": request})
    assert resp_email.status_code == status.HTTP_403_FORBIDDEN
    assert resp_email.data["error"]["code"] == "email_not_verified"

    resp_nf = custom_exception_handler(NotFoundError("Post not found"), {"request": request})
    assert resp_nf.status_code == status.HTTP_404_NOT_FOUND
    assert resp_nf.data["error"]["code"] == "not_found"


def test_custom_exception_handler_django_exceptions():
    factory = APIRequestFactory()
    request = factory.get("/")
    request.id = "req-dj-001"

    from django.core.exceptions import PermissionDenied as DjPermissionDenied
    from django.http import Http404

    resp_404 = custom_exception_handler(Http404(), {"request": request})
    assert resp_404.status_code == status.HTTP_404_NOT_FOUND

    resp_perm = custom_exception_handler(DjPermissionDenied(), {"request": request})
    assert resp_perm.status_code == status.HTTP_403_FORBIDDEN


def test_custom_exception_handler_unhandled_500():
    factory = APIRequestFactory()
    request = factory.get("/")
    request.id = "req-500-error"

    exc = RuntimeError("Database crashed unexpectedly")
    context = {"request": request}

    response = custom_exception_handler(exc, context)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data["error"]["code"] == "server_error"
    assert "Database crashed" not in response.data["error"]["message"]
    assert response.data["request_id"] == "req-500-error"
