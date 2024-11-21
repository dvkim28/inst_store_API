import os
import urllib.parse
from django.template.loader import render_to_string
from django.utils.html import strip_tags


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
    template_name = "mail_template/mailChangePass.html"
    convert_to_html_content = render_to_string(template_name)
    plain_message = strip_tags(convert_to_html_content)




    verification_link = f"{BASE_URL}#/confirm/{token}"


    send_mail(
        "Password recovery",
        message=plain_message,
        from_email="d.villarionovich@gmail.com",
        recipient_list= [mail,],
        html_message=convert_to_html_content,
        fail_silently=False,
    )
