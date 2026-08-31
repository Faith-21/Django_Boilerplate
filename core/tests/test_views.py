from django.test import TestCase
from django.urls import reverse


class PublicPageTests(TestCase):
    def test_home_is_public(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)

    def test_healthz_reports_ok(self):
        response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
