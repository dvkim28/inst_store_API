import os

import stripe
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Order
from config import settings


def create_checkout_session(order: Order) -> None:
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    try:
        line_items = []
        for item in order.items.all():
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
            success_url=settings.YOUR_DOMAIN + "/success.html",
            cancel_url=settings.YOUR_DOMAIN + "/cancel.html",
            metadata={
                "order_id": order.id,
            },
        )
        add_checkout_to_order(order=order, url=checkout_session.url)
        return checkout_session.url
    except stripe.error.StripeError as e:
        raise Exception(f"Stripe error: {str(e)}")


def add_checkout_to_order(url: str, order) -> None:
    order.checkout_url = url
    order.save()
