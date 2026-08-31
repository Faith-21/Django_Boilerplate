from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User


class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "full_name")


class AdminUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin tuned for the email-based user model."""

    add_form = AdminUserCreationForm
    form = AdminUserChangeForm
    change_password_form = AdminPasswordChangeForm
    model = User

    list_display = ("email", "full_name", "role", "is_active", "is_staff", "date_joined")
    list_filter = ("role", "is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("email", "full_name", "job_title")
    ordering = ("email",)
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("full_name", "job_title")}),
        (
            _("Access"),
            {
                "fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
                "description": _("Deactivate an account to revoke access without deleting its history."),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "role", "password1", "password2"),
            },
        ),
    )

    @admin.action(description=_("Deactivate selected users"))
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, _("%(count)d user(s) deactivated.") % {"count": updated})

    @admin.action(description=_("Activate selected users"))
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, _("%(count)d user(s) activated.") % {"count": updated})

    actions = ["activate_users", "deactivate_users"]
