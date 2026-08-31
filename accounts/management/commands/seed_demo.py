"""Create one account per role so the login flow can be tested by hand."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User

PASSWORD = "demo-passphrase-42"

DEMO_USERS = [
    ("admin@example.com", "Demo Administrator", User.Role.ADMIN, True),
    ("manager@example.com", "Demo Manager", User.Role.MANAGER, False),
    ("member@example.com", "Demo Member", User.Role.MEMBER, False),
]


class Command(BaseCommand):
    help = "Create demo accounts (one per role) for manual testing. Development only."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Create the accounts even when DEBUG=False. Never do this on a real deployment.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "Refusing to create demo accounts with known passwords while DEBUG=False. "
                "Pass --force only if you are certain this is a throwaway environment."
            )

        for email, full_name, role, is_staff in DEMO_USERS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"full_name": full_name, "role": role, "is_staff": is_staff},
            )
            user.full_name = full_name
            user.role = role
            user.is_staff = is_staff
            user.is_superuser = role == User.Role.ADMIN
            user.is_active = True
            user.set_password(PASSWORD)
            user.save()
            verb = "Created" if created else "Reset"
            self.stdout.write(f"{verb} {email:<22} role={role:<8} password={PASSWORD}")

        self.stdout.write(self.style.SUCCESS("\nDemo accounts ready. Sign in at /accounts/login/"))
        self.stdout.write("Expected: member cannot open /team/ (403); manager and admin can.")
