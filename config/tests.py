"""Tests for settings helpers — chiefly that a blank .env value is ignored."""

import os
from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase

from config.settings import env_str


class EnvStrTests(SimpleTestCase):
    """
    `.env.example` ships keys with empty values. A blank must fall back to the
    default rather than being passed through: a blank DATABASE_URL used to
    produce an unusable database config and crash on start-up.
    """

    def test_blank_value_falls_back_to_the_default(self):
        with mock.patch.dict(os.environ, {"SMOKE_TEST_KEY": ""}):
            self.assertEqual(env_str("SMOKE_TEST_KEY", "fallback"), "fallback")

    def test_whitespace_only_value_falls_back(self):
        with mock.patch.dict(os.environ, {"SMOKE_TEST_KEY": "   "}):
            self.assertEqual(env_str("SMOKE_TEST_KEY", "fallback"), "fallback")

    def test_a_real_value_wins(self):
        with mock.patch.dict(os.environ, {"SMOKE_TEST_KEY": " provided "}):
            self.assertEqual(env_str("SMOKE_TEST_KEY", "fallback"), "provided")

    def test_missing_key_uses_the_default(self):
        self.assertEqual(env_str("NOT_SET_ANYWHERE_KEY", "fallback"), "fallback")

    def test_the_database_is_configured(self):
        """A blank DATABASE_URL must still leave a usable database."""
        self.assertIn("ENGINE", settings.DATABASES["default"])
        self.assertTrue(settings.DATABASES["default"]["ENGINE"])
