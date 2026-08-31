"""
Per-IP login attempt limiting.

Failures are counted in the cache. LocMemCache (the default) is per-process,
which is enough to slow down casual guessing; point CACHE_URL at Redis or
Memcached when the app runs on more than one worker.
"""

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

LOCKOUT_MESSAGE = _("Too many failed attempts. Wait a few minutes before trying again.")


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    return forwarded or request.META.get("REMOTE_ADDR", "")


def _key(request):
    return f"login-attempts:{client_ip(request)}"


def failure_count(request):
    return cache.get(_key(request), 0)


def record_failure(request):
    """Count one failed attempt and return the new total."""
    attempts = failure_count(request) + 1
    cache.set(_key(request), attempts, settings.LOGIN_RATELIMIT_WINDOW)
    return attempts


def clear_failures(request):
    cache.delete(_key(request))


def is_locked_out(request):
    return failure_count(request) >= settings.LOGIN_RATELIMIT_ATTEMPTS
