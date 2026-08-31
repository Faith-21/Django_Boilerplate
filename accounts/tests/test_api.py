from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts.models import User

PASSWORD = "correct-horse-9"


class AuthAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="jane@example.com", password=PASSWORD, full_name="Jane Doe"
        )

    def test_login_returns_a_token(self):
        response = self.client.post(
            reverse("accounts-api:login"),
            {"email": "jane@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Token.objects.filter(key=response.data["token"], user=self.user).exists())
        self.assertEqual(response.data["user"]["email"], "jane@example.com")

    def test_login_rejects_bad_credentials(self):
        response = self.client.post(
            reverse("accounts-api:login"),
            {"email": "jane@example.com", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_me_requires_authentication(self):
        # 401 (not 403) because TokenAuthentication is first in the chain and
        # supplies a WWW-Authenticate header.
        self.assertEqual(self.client.get(reverse("accounts-api:me")).status_code, 401)

    def test_a_revoked_token_stops_working(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertEqual(self.client.get(reverse("accounts-api:me")).status_code, 200)
        Token.objects.filter(user=self.user).delete()
        self.assertEqual(self.client.get(reverse("accounts-api:me")).status_code, 401)

    def test_me_returns_and_updates_the_caller(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("accounts-api:me"))
        self.assertEqual(response.data["email"], "jane@example.com")

        response = self.client.patch(reverse("accounts-api:me"), {"job_title": "Analyst"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.job_title, "Analyst")

    def test_role_is_read_only_over_the_api(self):
        self.client.force_authenticate(self.user)
        self.client.patch(reverse("accounts-api:me"), {"role": User.Role.ADMIN}, format="json")
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.MEMBER)

    def test_logout_revokes_the_token(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post(reverse("accounts-api:logout"))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_password_change_rotates_the_token(self):
        old_token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {old_token.key}")
        response = self.client.post(
            reverse("accounts-api:password-change"),
            {"current_password": PASSWORD, "new_password": "another-good-passphrase-7"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data["token"], old_token.key)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("another-good-passphrase-7"))

    def test_password_change_requires_the_current_password(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("accounts-api:password-change"),
            {"current_password": "wrong-password", "new_password": "another-good-passphrase-7"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
