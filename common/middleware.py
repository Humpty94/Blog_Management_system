import threading
import uuid

_thread_locals = threading.local()


def get_current_request_id():
    """Retrieve the current request ID from thread-local storage."""
    return getattr(_thread_locals, "request_id", None)


class RequestIDMiddleware:
    """
    Middleware that generates or propagates a unique X-Request-ID for every HTTP request.
    Attaches the ID to the request object, thread-local storage, and the response headers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract existing X-Request-ID or generate a new UUIDv4
        request_id = request.META.get("HTTP_X_REQUEST_ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        request.id = request_id
        _thread_locals.request_id = request_id

        try:
            response = self.get_response(request)
        finally:
            _thread_locals.request_id = None

        response["X-Request-ID"] = request_id
        return response
