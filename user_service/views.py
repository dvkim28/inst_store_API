from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response

from user_service.serializers import ManageUserSerializer, UserSerializer


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
