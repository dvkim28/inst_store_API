from django.utils import timezone
import datetime

import os

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from user_service.models import PasswordReset
from user_service.serializers import (
    ManageUserSerializer,
    UserSerializer,
    ResetPasswordRequestSerializer,
    ResetPasswordSerializer,
)
from user_service.utils import send_recovery_email


class UserModelView(viewsets.ModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = ManageUserSerializer
    queryset = get_user_model().objects.all()

    def get_object(self):
        return self.request.user


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.AllowAny,)


class VerifyEmailView(generics.GenericAPIView):
    def get(self, request):
        token = request.query_params.get("token", None)

        if not token:
            return Response(
                {"error": "Токен отсутствует"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = get_user_model().objects.get(verification_token=token)
        except get_user_model().DoesNotExist:
            return Response(
                {"error": "Пользователь с данным токеном не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_email_verified:
            return Response(
                {"error": "Электронная почта уже подтверждена"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_email_verified = True
        user.verification_token = None
        user.save()
        return Response(
            {"message": "Электронная почта успешно подтверждена"},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordRequestSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = ResetPasswordRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get("email")
            try:
                get_user_model().objects.get(email=email)
                send_recovery_email(email)
                return Response(
                    {"message": "Password recovery email sent successfully."},
                    status=status.HTTP_200_OK,
                )
            except get_user_model().DoesNotExist:
                return Response(
                    {"message": "This email is not registered/existing"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirm(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        token = request.GET.get("token")
        today = timezone.now()

        if not token:
            return Response(
                {"message": "Token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            password_reset = PasswordReset.objects.get(token=token)
            user = get_user_model().objects.get(email=password_reset.email)
        except PasswordReset.DoesNotExist:
            return Response(
                {"message": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if today - password_reset.created_at > datetime.timedelta(hours=1):
            return Response(
                {"message": "Expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.is_email_verified is False:
            return Response(
                {"message": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            new_password = serializer.validated_data["new_password"]

            try:
                user = get_user_model().objects.get(email=password_reset.email)
            except ObjectDoesNotExist:
                return Response(
                    {"message": "User not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            user.set_password(new_password)
            user.save()
            password_reset.delete()
            return Response(
                {"message": "Password reset successful."},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
