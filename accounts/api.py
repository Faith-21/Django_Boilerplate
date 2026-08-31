"""
JSON API for authentication.

Endpoints (mounted under /api/auth/ by config/urls.py):

    POST /api/auth/login/     {"email", "password"} -> {"token", "user"}
    POST /api/auth/logout/    revokes the token and clears the session
    GET  /api/auth/me/        the signed-in user
    PATCH/api/auth/me/        update full_name / job_title
    POST /api/auth/password/  {"current_password", "new_password"}

Token auth suits scripts and mobile clients; a browser front-end on the same
site can use the session cookie instead and skip the login endpoint entirely.
"""

from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .serializers import LoginSerializer, PasswordChangeSerializer, UserSerializer


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class LoginAPIView(APIView):
    """Exchange email + password for an auth token (and a session cookie)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _created = Token.objects.get_or_create(user=user)
        django_login(request, user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class LogoutAPIView(APIView):
    """Revoke the caller's token and end the session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeAPIView(generics.RetrieveUpdateAPIView):
    """Read or update the signed-in user's own profile."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordChangeAPIView(APIView):
    """Change the signed-in user's password and rotate their token."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        return Response({"token": token.key})
