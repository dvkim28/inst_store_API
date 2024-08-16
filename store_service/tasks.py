import os

import django
import requests
from celery import Celery, shared_task
from django.contrib.auth import get_user_model

from .models import Order
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

app = Celery("telegram_bot", broker="redis://localhost")
TG_TOKEN = settings.TG_TOKEN
CHAT_ID = settings.CHAT_ID

from celery import shared_task
import requests
from django.contrib.auth import get_user_model
from .models import Order, OrderItem


@shared_task
def send_telegram_message(order_id: int) -> None:
    try:
        order = Order.objects.get(id=order_id)

        user = get_user_model().objects.get(id=order.user_id)

        order_items = OrderItem.objects.filter(order=order)
        items_detail = "\n".join(
            [
                f"{item.item.name} (Size: {item.size}, Color: {item.color}) - {item.quantity} x {item.price} each"
                for item in order_items]
        )

        message = (
            f"New Order Received!\n\n"
            f"User: {user.email}\n"
            f"Delivery Address: {order.delivery_address}\n"
            f"Order Date: {order.created_at}\n"
            f"Total Items: {order_items.count()}\n\n"
            f"Order Details:\n{items_detail}\n\n"
            f"Order ID: {order.id}\n"
            f"Checkout URL: {order.checkout_url}"
        )

        url = (
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            f"?chat_id={CHAT_ID}&text={message}"
        )

        response = requests.get(url)
        response.raise_for_status()

    except Exception as e:
        print(f"Error sending Telegram message: {e}")
