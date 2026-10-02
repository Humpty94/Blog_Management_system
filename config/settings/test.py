from .base import *  # noqa: F403

DEBUG = False
TESTING = True

# Speed up test password hashing
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Use in-memory email backend for testing
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Test runner and database settings
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "blog_db",
        "USER": "deepak_sharma",
        "PASSWORD": "",
        "HOST": "127.0.0.1",
        "PORT": "5432",
        "TEST": {
            "NAME": "test_blog_db",
        },
    }
}

# High throttle rates for tests so test suites can run without getting throttled
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ()  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "auth": "10000/minute",
    "write": "10000/minute",
}

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
