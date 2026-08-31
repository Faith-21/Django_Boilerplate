"""
Settings used by the test suite: `python manage.py test --settings=config.test_settings`.

Identical to the normal settings apart from speed and isolation tweaks.
"""

from .settings import *  # noqa: F403

DEBUG = False

# Hashing passwords properly is deliberately slow; tests do not need it.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# A per-run cache keeps the login throttle from leaking between test cases.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "tests"}}

DATABASES = {  # noqa: F405
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:", "ATOMIC_REQUESTS": True}
}

# WhiteNoise only matters for real static-file serving; skipping it keeps the
# test output free of "no staticfiles directory" warnings.
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]  # noqa: F405

# Keep the test output readable; the views still log as usual in real runs.
LOGGING["root"]["level"] = "CRITICAL"  # noqa: F405
LOGGING["loggers"]["accounts"]["level"] = "CRITICAL"  # noqa: F405
