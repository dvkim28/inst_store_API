import urllib.parse

from django.core.mail import send_mail
from django.utils.crypto import get_random_string


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


def send_reset_password_via_email(mail:str, reset_password_link:str):

    reset_link = reset_password_link
    message = (
        f"Привет!"
        f"Пожалуйста, перейдите по ссылке"
        f" для подтверждения вашей почты:{reset_link}"
    )

    send_mail(
        f"Reset password for {mail}",
        message,
        "d.villarionovich@gmail.com",
        [mail],
        fail_silently=False,
    )