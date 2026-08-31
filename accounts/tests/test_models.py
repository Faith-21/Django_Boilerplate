from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User


class UserModelTests(TestCase):
    def test_create_user_normalises_email(self):
        user = User.objects.create_user(email="  Jane.Doe@Example.COM ".strip(), password="correct-horse-9")
        self.assertEqual(user.email, "jane.doe@example.com")
        self.assertTrue(user.check_password("correct-horse-9"))
        self.assertEqual(user.role, User.Role.MEMBER)
        self.assertFalse(user.is_staff)

    def test_email_is_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="correct-horse-9")

    def test_email_must_be_unique(self):
        User.objects.create_user(email="a@example.com", password="correct-horse-9")
        with self.assertRaises(ValidationError):
            User.objects.create_user(email="A@example.com", password="correct-horse-9")

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="root@example.com", password="correct-horse-9")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, User.Role.ADMIN)

    def test_has_role(self):
        member = User.objects.create_user(email="m@example.com", password="correct-horse-9")
        manager = User.objects.create_user(
            email="mgr@example.com", password="correct-horse-9", role=User.Role.MANAGER
        )
        admin = User.objects.create_superuser(email="root@example.com", password="correct-horse-9")

        self.assertFalse(member.has_role(User.Role.MANAGER))
        self.assertTrue(manager.has_role(User.Role.MANAGER))
        self.assertTrue(admin.has_role(User.Role.MANAGER), "admins pass every role check")
