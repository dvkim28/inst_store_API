import os
import urllib.parse

from django.core.mail import send_mail
from django.utils.crypto import get_random_string

from user_service.models import PasswordReset


def send_verification_email(user):
    token = get_random_string(length=32)
    user.verification_token = token
    user.save()

    verification_link = (
        f"http://127.0.0.1:5173/#/activate/?token={urllib.parse.quote(token)}"
    )

    message = (
        f"Привет, {user.username}!"
        f"Пожалуйста, перейдите по ссылке"
        f" для подтверждения вашей почты: {verification_link}"
    )

    send_mail(
        "Подтверждение почты",
        message,
        "d.villarionovich@gmail.com",
        [user.email],
        fail_silently=False,
    )


def send_recovery_email(mail: str) -> None:
    token = get_random_string(length=32)
    pass_reset = PasswordReset.objects.create(email=mail, token=token)
    pass_reset.save()
    BASE_URL = os.environ.get("BASE_URL")

    verification_link = f"{BASE_URL}#/confirm/{token}"
    message = (
        f"Hello!\n\n"
        f"We received a request to reset the password for your account. "
        f"Please click the following link to set a new password:\n\n"
        f"{verification_link}\n\n"
        f"If you did not request a password reset, please ignore this message."
    )

    send_mail(
        "Password recovery",
        message,
        "d.villarionovich@gmail.com",
        [mail],
        fail_silently=False,
    )
