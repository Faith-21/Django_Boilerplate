from django.test import TestCase
from django.urls import reverse

from accounts.models import User

PASSWORD = "correct-horse-9"


class RoleAccessTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(email="member@example.com", password=PASSWORD)
        self.manager = User.objects.create_user(
            email="manager@example.com", password=PASSWORD, role=User.Role.MANAGER
        )
        self.admin = User.objects.create_superuser(email="admin@example.com", password=PASSWORD)

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse("core:team"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_member_is_forbidden(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("core:team")).status_code, 403)

    def test_manager_is_allowed(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("core:team")).status_code, 200)

    def test_admin_is_allowed(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("core:team")).status_code, 200)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertIn(reverse("accounts:login"), response["Location"])

        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 200)
