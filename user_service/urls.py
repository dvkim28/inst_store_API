from django.contrib.auth.views import LoginView
from django.urls import path
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView)

from user_service.views import (ManageUserView, UserRegistrationView,
                                VerifyEmailView, ResetPassword, RequestPasswordReset)

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="registration"),
    path("me/", ManageUserView.as_view(), name="manage-user"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("verifying/", VerifyEmailView.as_view(), name="verifying_email"),
    path("reset_password/", RequestPasswordReset.as_view(), name="reset_password"),
    path("password_recovery/", ResetPassword.as_view(), name="recovery_password"),
]

app_name = "user_service"
