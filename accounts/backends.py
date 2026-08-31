from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailBackend(ModelBackend):
    """
    Authenticate with an email address, case-insensitively.

    Emails are stored lower-cased, but people type them however they like, so
    the lookup is case-insensitive and a password hash is still run when no
    user matches to keep response times uniform.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get("email")
        if email is None or password is None:
            return None
        try:
            user = UserModel.objects.get(email__iexact=email.strip())
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
