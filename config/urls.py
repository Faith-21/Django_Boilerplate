"""
URL routing.

    /                  public landing page
    /dashboard/        signed-in landing page
    /team/             manager-only example page
    /accounts/...      login, logout, signup, profile, password reset
    /api/auth/...      JSON auth endpoints (delete accounts/api*.py to drop)
    /admin/            Django admin
    /healthz/          health probe
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import healthz

urlpatterns = [
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("api/auth/", include("accounts.api_urls")),
    path("admin/", admin.site.urls),
    path("healthz/", healthz, name="healthz"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = f"{settings.SITE_NAME} administration"
admin.site.site_title = settings.SITE_NAME
admin.site.index_title = "Manage accounts and data"
