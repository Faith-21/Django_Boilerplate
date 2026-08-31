from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Manager for the email-based user model."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", User.Role.MEMBER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Department user, identified by email address rather than a username.

    `role` is the coarse access level used by the `role_required` decorator and
    `RoleRequiredMixin`. Use Django groups and permissions on top of it when a
    project needs finer-grained rules.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", _("Administrator")
        MANAGER = "manager", _("Manager")
        MEMBER = "member", _("Member")

    email = models.EmailField(_("email address"), unique=True)
    full_name = models.CharField(_("full name"), max_length=150, blank=True)
    job_title = models.CharField(_("job title"), max_length=150, blank=True)
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        help_text=_("Coarse access level checked by role_required / RoleRequiredMixin."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Unselect this instead of deleting an account to revoke access."),
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into the Django admin site."),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["email"]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = self.__class__.objects.normalize_email(self.email).lower()
        return super().save(*args, **kwargs)

    def get_full_name(self):
        return self.full_name or self.email

    def get_short_name(self):
        return self.full_name.split(" ")[0] if self.full_name else self.email.split("@")[0]

    @property
    def is_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_manager(self):
        return self.is_admin or self.role == self.Role.MANAGER

    def has_role(self, *roles):
        """True when the user holds any of `roles` (admins always pass)."""
        return self.is_admin or self.role in roles
