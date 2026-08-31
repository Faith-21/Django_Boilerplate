import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, UpdateView

from .forms import LoginForm, ProfileForm, SignupForm

logger = logging.getLogger(__name__)


def _throttle_key(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    ip = forwarded or request.META.get("REMOTE_ADDR", "")
    return f"login-attempts:{ip}"


class LoginView(auth_views.LoginView):
    """
    Email/password login with a simple per-IP attempt limit.

    The limiter uses the configured cache. LocMemCache (the default) is
    per-process, which is enough to slow down casual guessing; point CACHES at
    Redis or Memcached when the app runs on more than one worker.
    """

    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        cache.delete(_throttle_key(self.request))
        logger.info("Successful login for %s", form.get_user().email)
        return super().form_valid(form)

    def form_invalid(self, form):
        key = _throttle_key(self.request)
        attempts = cache.get(key, 0) + 1
        cache.set(key, attempts, settings.LOGIN_RATELIMIT_WINDOW)
        logger.warning("Failed login attempt %s from %s", attempts, key)
        if attempts >= settings.LOGIN_RATELIMIT_ATTEMPTS:
            form.add_error(
                None,
                _("Too many failed attempts. Wait a few minutes before trying again."),
            )
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        if cache.get(_throttle_key(request), 0) >= settings.LOGIN_RATELIMIT_ATTEMPTS:
            form = self.get_form()
            form.add_error(None, _("Too many failed attempts. Wait a few minutes before trying again."))
            return self.form_invalid(form)
        return super().post(request, *args, **kwargs)


class LogoutView(auth_views.LogoutView):
    """Log out on POST only (Django's default since 5.0) and confirm it."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.success(request, _("You have been signed out."))
        return response


class SignupView(CreateView):
    """Self-service registration; disable it with SIGNUP_OPEN=False."""

    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")

    def dispatch(self, request, *args, **kwargs):
        if not settings.SIGNUP_OPEN:
            messages.info(
                request,
                _("Accounts are created by a department administrator. Please request access."),
            )
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def handle_no_permission(self):
        return redirect("accounts:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info("New account registered: %s", self.object.email)
        messages.success(self.request, _("Account created. You can sign in now."))
        return response


class ProfileView(LoginRequiredMixin, UpdateView):
    """Let a signed-in user maintain their own details."""

    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, _("Your profile has been updated."))
        return super().form_valid(form)


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("accounts:password_change_done")


class PasswordResetView(auth_views.PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.txt"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")
