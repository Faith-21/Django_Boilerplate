from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User


class StyledFormMixin:
    """Give every widget the shared CSS class used by the templates."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{css} field__input".strip()


class LoginForm(StyledFormMixin, AuthenticationForm):
    """Email + password login, with a friendlier error message."""

    username = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(
            attrs={"autofocus": True, "autocomplete": "email", "placeholder": "you@example.com"}
        ),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": _("That email and password combination is not recognised."),
        "inactive": _("This account has been deactivated. Contact a department administrator."),
    }


class SignupForm(StyledFormMixin, UserCreationForm):
    """Self-service registration, optionally restricted to department domains."""

    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )

    class Meta:
        model = User
        fields = ("email", "full_name", "job_title")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        allowed = [d.lower().lstrip("@") for d in settings.SIGNUP_ALLOWED_EMAIL_DOMAINS]
        if allowed and email.rsplit("@", 1)[-1] not in allowed:
            raise forms.ValidationError(
                _("Registration is limited to these email domains: %(domains)s."),
                params={"domains": ", ".join(allowed)},
            )
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("An account with this email address already exists."))
        return email


class ProfileForm(StyledFormMixin, forms.ModelForm):
    """The fields a user may edit about themselves (role is not one of them)."""

    class Meta:
        model = User
        fields = ("full_name", "job_title")
