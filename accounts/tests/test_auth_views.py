from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User

PASSWORD = "correct-horse-9"


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password=PASSWORD, full_name="Jane Doe"
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")

    def test_login_succeeds_and_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "jane@example.com", "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("core:dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_login_is_case_insensitive_on_email(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "JANE@Example.com", "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("core:dashboard"))

    def test_login_fails_with_wrong_password(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "jane@example.com", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_deactivated_user_cannot_log_in(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "jane@example.com", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(LOGIN_RATELIMIT_ATTEMPTS=3)
    def test_repeated_failures_are_throttled(self):
        from django.core.cache import cache

        cache.clear()
        for _ in range(3):
            self.client.post(
                reverse("accounts:login"), {"username": "jane@example.com", "password": "wrong-password"}
            )
        response = self.client.post(
            reverse("accounts:login"), {"username": "jane@example.com", "password": PASSWORD}
        )
        self.assertContains(response, "Too many failed attempts")
        self.assertNotIn("_auth_user_id", self.client.session)
        cache.clear()

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)


class SignupTests(TestCase):
    def test_signup_creates_a_member_account(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "new@example.com",
                "full_name": "New Person",
                "job_title": "Analyst",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("accounts:login"))
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.role, User.Role.MEMBER)
        self.assertFalse(user.is_staff)

    @override_settings(SIGNUP_ALLOWED_EMAIL_DOMAINS=["dept.example.edu"])
    def test_signup_rejects_outside_domains(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "outsider@gmail.com",
                "full_name": "Outsider",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="outsider@gmail.com").exists())

    @override_settings(SIGNUP_OPEN=False)
    def test_signup_can_be_closed(self):
        response = self.client.get(reverse("accounts:signup"))
        self.assertRedirects(response, reverse("accounts:login"))


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password=PASSWORD)

    def test_reset_email_is_sent_with_a_working_link(self):
        response = self.client.post(reverse("accounts:password_reset"), {"email": "jane@example.com"})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)

        link = [line for line in mail.outbox[0].body.splitlines() if "/accounts/password/reset/" in line][0]
        path = link.split("://")[1].split("/", 1)[1]
        response = self.client.get(f"/{path}", follow=True)
        self.assertEqual(response.status_code, 200)

    def test_unknown_address_does_not_leak(self):
        response = self.client.post(reverse("accounts:password_reset"), {"email": "nobody@example.com"})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password=PASSWORD)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_user_can_update_own_details(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:profile"), {"full_name": "Jane Q. Doe", "job_title": "Lead"}
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Jane Q. Doe")

    def test_user_cannot_escalate_their_own_role(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("accounts:profile"),
            {"full_name": "Jane", "job_title": "Lead", "role": User.Role.ADMIN, "is_staff": True},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.MEMBER)
        self.assertFalse(self.user.is_staff)
