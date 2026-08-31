from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connection
from django.http import JsonResponse
from django.views.generic import TemplateView

from accounts.models import User
from accounts.permissions import RoleRequiredMixin


class HomeView(TemplateView):
    """Public landing page — the only page anonymous visitors can see."""

    template_name = "core/home.html"


class DashboardView(LoginRequiredMixin, TemplateView):
    """The page people land on after signing in. Replace with your project."""

    template_name = "core/dashboard.html"


class TeamView(RoleRequiredMixin, TemplateView):
    """
    Example of a page limited to a role.

    Members see the dashboard; only managers and admins can list the team.
    """

    template_name = "core/team.html"
    required_roles = [User.Role.MANAGER]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["members"] = User.objects.order_by("full_name", "email")
        return context


def healthz(request):
    """Liveness/readiness probe for load balancers and container platforms."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database_ok = True
    except Exception:  # pragma: no cover - only hit when the database is down
        database_ok = False
    status = 200 if database_ok else 503
    return JsonResponse(
        {"status": "ok" if database_ok else "degraded", "database": database_ok}, status=status
    )
