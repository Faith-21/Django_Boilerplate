"""Reusable role checks for views (function-based, class-based and DRF)."""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


def role_required(*roles):
    """
    Restrict a function-based view to users holding one of `roles`.

        @role_required(User.Role.MANAGER)
        def budget_report(request): ...

    Anonymous users are sent to the login page; signed-in users without the
    role get a 403.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not request.user.has_role(*roles):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


class RoleRequiredMixin:
    """
    Class-based view equivalent of `role_required`.

        class BudgetReport(RoleRequiredMixin, TemplateView):
            required_roles = [User.Role.MANAGER]
    """

    required_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.has_role(*self.required_roles):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class HasRole(BasePermission):
    """
    DRF permission counterpart.

        class BudgetViewSet(ModelViewSet):
            permission_classes = [HasRole.of(User.Role.MANAGER)]
    """

    roles = ()

    @classmethod
    def of(cls, *roles):
        return type("HasRole", (cls,), {"roles": roles})

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.has_role(*self.roles))
