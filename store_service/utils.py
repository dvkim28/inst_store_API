import os

import stripe
from celery import shared_task
from deep_translator import GoogleTranslator
from django.apps import apps
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from config import settings
from store_service.models import Order
from user_service.models import User


def create_checkout_session(order_id: int) -> str:
    from store_service.models import Order

    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        raise ValueError(
            "Stripe secret key " "is not set in environment variables"
        )

    try:
        order = Order.objects.get(id=order_id)
        line_items = []
        for item in order.items.all():
            print(item.price)
            product = stripe.Product.create(
                name=item.item.name,
                description=item.item.description,
            )
            price = stripe.Price.create(
                unit_amount=int(item.price * 100),
                currency="usd",
                product=product.id,
            )

            line_items.append(
                {
                    "price": price.id,
                    "quantity": 1,
                }
            )

        checkout_session = stripe.checkout.Session.create(
            line_items=line_items,
            mode="payment",
            success_url=f"{settings.YOUR_DOMAIN}/success.html",
            cancel_url=f"{settings.YOUR_DOMAIN}/cancel.html",
            metadata={
                "order_id": order.id,
            },
        )
        add_checkout_to_order(order=order, url=checkout_session.url)
        return checkout_session.url
    except stripe.error.StripeError as e:
        raise Exception(f"Stripe error: {str(e)}")


def add_checkout_to_order(order, url: str) -> None:
    order.checkout_url = url
    order.save()


@shared_task
def translate_and_update_category(category_id: int) -> None:
    try:
        Category = apps.get_model("store_service", "Category")
        category = Category.objects.get(id=category_id)
        translator = GoogleTranslator(source="en", target="ua")
        translated_name = translator.translate(category.name)
        translated_description = translator.translate(category.description)
        category.name_uk = translated_name
        category.description_uk = translated_description
        category.save()
    except Exception as e:
        print(f"Ошибка при переводе и обновлении модели: {e}")


@shared_task
def translate_and_update_item(item_id: int) -> None:
    try:
        Item = apps.get_model("store_service", "Item")
        item = Item.objects.get(id=item_id)
        translator = GoogleTranslator(source="en", target="ua")

        item_name = translator.translate(item.name)
        item_fabric = translator.translate(item.fabric)

        item.name_uk = item_name
        item.fabric_uk = item_fabric

        item.save()
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при переводе и обновлении модели: {e}")


@shared_task
def translate_and_update_description(item_id: int) -> None:
    try:
        i_descr = apps.get_model("store_service", "ItemDescription")
        ids = i_descr.objects.get(id=item_id)
        translator = GoogleTranslator(source="en", target="ua")

        ids.title_uk = translator.translate(ids.title)
        ids.description_uk = translator.translate(ids.description)

        ids.save()
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при переводе ids и обновлении модели: {e}")


def send_email_order_created(order: Order, user: User) -> None:
    message = (
        f"Hello!\n\n"
        f"You just recieved a new order, order ID is {order}\n "
        f"from {user.email}"
    )
    print(f"message:{message}")

    send_mail(
        f"New order from {user.email}",
        message,
        "d.villarionovich@gmail.com",
        ["d.villarionovich@gmail.com",],
        fail_silently=False,
    )


def send_email_to_user_about_order_success(order, user) -> None:
    print("message starting")
    template_name = "mail_template/successOrder.html"
    total = get_total_price(order)
    order_items = order.items.all()

    convert_to_html_content = render_to_string(template_name, {
        'order_items': order_items,
        'total': total,
        'user': user})
    plain_message = strip_tags(convert_to_html_content)

    send_mail(
        subject="We recieved your order",
        message=plain_message,
        from_email="d.villarionovich@gmail.com",
        recipient_list=[user.email,],
        html_message=convert_to_html_content,
        fail_silently=True
    )


def get_total_price(order):
    return sum(item.price * item.quantity for item in order.items.all())
