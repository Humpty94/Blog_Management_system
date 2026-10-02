from rest_framework.throttling import SimpleRateThrottle


class AuthRateThrottle(SimpleRateThrottle):
    """
    Throttle for authentication endpoints (login, register, token refresh).
    Identifies clients by IP address.
    """

    scope = "auth"

    def get_cache_key(self, request, view):
        return self.get_ident(request)


class WriteRateThrottle(SimpleRateThrottle):
    """
    Throttle for state-mutating write endpoints (POST, PUT, PATCH, DELETE).
    Uses authenticated user ID if logged in, otherwise falls back to client IP.
    """

    scope = "write"

    def get_cache_key(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return None  # Public reads are never throttled

        if request.user and request.user.is_authenticated:
            return f"throttle_write_user_{request.user.pk}"
        return f"throttle_write_ip_{self.get_ident(request)}"
