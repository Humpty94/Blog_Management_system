import uuid

from django.http import HttpResponse
from django.test import RequestFactory

from common.middleware import RequestIDMiddleware, get_current_request_id


def dummy_view(request):
    return HttpResponse("ok")


def test_request_id_middleware_generates_id():
    factory = RequestFactory()
    request = factory.get("/")
    middleware = RequestIDMiddleware(dummy_view)

    response = middleware(request)

    assert hasattr(request, "id")
    assert response.has_header("X-Request-ID")
    assert response["X-Request-ID"] == request.id
    # Ensure it's a valid UUID
    uuid_obj = uuid.UUID(request.id)
    assert str(uuid_obj) == request.id


def test_request_id_middleware_preserves_custom_id():
    custom_id = "custom-client-trace-id-12345"
    factory = RequestFactory()
    request = factory.get("/", HTTP_X_REQUEST_ID=custom_id)
    middleware = RequestIDMiddleware(dummy_view)

    response = middleware(request)

    assert request.id == custom_id
    assert response["X-Request-ID"] == custom_id


def test_thread_local_cleaned_up_after_request():
    factory = RequestFactory()
    request = factory.get("/")

    captured_during_request = None

    def inspecting_view(req):
        nonlocal captured_during_request
        captured_during_request = get_current_request_id()
        return HttpResponse("ok")

    middleware = RequestIDMiddleware(inspecting_view)
    middleware(request)

    assert captured_during_request is not None
    assert get_current_request_id() is None
