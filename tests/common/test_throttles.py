from django.contrib.auth import get_user_model
from django.test import RequestFactory
from rest_framework.views import APIView

from common.throttles import AuthRateThrottle, WriteRateThrottle

User = get_user_model()


def test_auth_rate_throttle_uses_ip():
    factory = RequestFactory()
    request = factory.post("/api/v1/auth/login/", REMOTE_ADDR="192.168.1.50")
    throttle = AuthRateThrottle()
    view = APIView()

    ident = throttle.get_cache_key(request, view)
    assert ident == "192.168.1.50"


def test_write_rate_throttle_ignores_reads():
    factory = RequestFactory()
    request = factory.get("/api/v1/posts/")
    throttle = WriteRateThrottle()
    view = APIView()

    assert throttle.get_cache_key(request, view) is None


def test_write_rate_throttle_uses_user_id_when_authenticated():
    factory = RequestFactory()
    request = factory.post("/api/v1/posts/")
    user = User(id=42, email="author@example.com", username="author")
    request.user = user

    throttle = WriteRateThrottle()
    view = APIView()

    cache_key = throttle.get_cache_key(request, view)
    assert cache_key == "throttle_write_user_42"


def test_write_rate_throttle_uses_ip_when_anonymous():
    factory = RequestFactory()
    request = factory.post("/api/v1/posts/", REMOTE_ADDR="10.0.0.99")
    from django.contrib.auth.models import AnonymousUser

    request.user = AnonymousUser()

    throttle = WriteRateThrottle()
    view = APIView()

    cache_key = throttle.get_cache_key(request, view)
    assert cache_key == "throttle_write_ip_10.0.0.99"
