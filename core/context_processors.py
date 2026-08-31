from django.conf import settings


def site(request):
    """Expose a couple of settings to every template."""
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SIGNUP_OPEN": settings.SIGNUP_OPEN,
    }
