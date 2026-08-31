from django.urls import path

from . import api

app_name = "accounts-api"

urlpatterns = [
    path("login/", api.LoginAPIView.as_view(), name="login"),
    path("logout/", api.LogoutAPIView.as_view(), name="logout"),
    path("me/", api.MeAPIView.as_view(), name="me"),
    path("password/", api.PasswordChangeAPIView.as_view(), name="password-change"),
]
