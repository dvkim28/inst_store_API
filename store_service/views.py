import stripe
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import (
    Basket,
    Category,
    Item,
    Order,
    OrderItem,
    BasketItem,
    ItemSize,
    ItemColor,
    ItemInventory, DeliveryInfo,
)
from .serializers import (
    BasketSerializer,
    CategorySerializer,
    ItemDetailSerializer,
    ItemSerializer,
    OrderSerializer,
    BasketItemSerializer,
    CategoryDetailSerializer,
)

from user_service.models import User

from config import settings


@extend_schema_view(
    list=extend_schema(
        summary="List items",
        description="Retrieve a list of items, with optional filters for size,"
                    " color, brand, sale status, stock status, and ordering.",
        responses={200: ItemSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve an item",
        description="Retrieve detailed information about a specific item.",
        responses={200: ItemDetailSerializer},
    ),
)
class ItemModelViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer
    queryset = Item.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ItemDetailSerializer
        return self.serializer_class

    def get_queryset(self):
        queryset = Item.objects.all()
        size = self.request.query_params.get("size", None)
        if size:
            queryset = queryset.filter(size__contains=size)
        color = self.request.query_params.get("color", None)
        if color:
            queryset = queryset.filter(color__contains=color)
        brand = self.request.query_params.get("brand", None)
        if brand:
            queryset = queryset.filter(brand__contains=brand)
        sale = self.request.query_params.get("sale", None)
        if sale:
            sale = sale.lower() == "true"
            queryset = queryset.filter(sale=sale)
        in_stock = self.request.query_params.get("in_stock", None)
        if in_stock:
            in_stock = in_stock.lower() == "true"
            queryset = queryset.filter(in_stock=in_stock)
        ordering = self.request.query_params.get("ordering", None)
        if ordering:
            if ordering.lower() == "newest":
                queryset = queryset.order_by("-id")
            elif ordering.lower() == "cheaper":
                queryset = queryset.order_by("price")
            elif ordering.lower() == "exp":
                queryset = queryset.order_by("-price")
        return queryset


@extend_schema_view(
    create=extend_schema(
        summary="Create a basket",
        description="Create a new basket " "for the current user and add items to it.",
        responses={201: BasketSerializer},
    ),
)
class BasketModelViewSet(viewsets.ModelViewSet):
    serializer_class = BasketSerializer
    queryset = Basket.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        basket, created = Basket.objects.get_or_create(user=self.request.user)
        items = serializer.validated_data.get("items", [])
        for item in items:
            basket.items.add(item)
        basket.save()

    def get_serializer_class(self):
        if self.action == "create":
            return BasketSerializer
        return BasketSerializer

    def get_queryset(self):
        return Basket.objects.filter(user=self.request.user)


class BasketItemViewSet(viewsets.ModelViewSet):
    serializer_class = BasketItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return BasketItem.objects.filter(basket__user=user)

    def create(self, request, *args, **kwargs):
        item = request.data.get("item")
        size = request.data.get("size")
        color = request.data.get("color")
        quantity = request.data.get("quantity", 1)
        print(f"item: {item}, size: {size}, color: {color}, quantity: {quantity}")
        try:
            item = Item.objects.get(name=item)
            size = ItemSize.objects.get(size=size)
            color = ItemColor.objects.get(color=color)
            inventory = ItemInventory.objects.get(item=item, size=size, color=color)

            if inventory.quantity < int(quantity):
                return Response(
                    {"error": "Not enough items in stock 134"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except (
                Item.DoesNotExist,
                ItemSize.DoesNotExist,
                ItemColor.DoesNotExist,
                ItemInventory.DoesNotExist,
        ):
            return Response(
                {"error": "Item, size, color, or inventory not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        basket, _ = Basket.objects.get_or_create(user=request.user)

        basket_item, created = BasketItem.objects.get_or_create(
            basket=basket,
            item=item,
            size=size,
            color=color,
            defaults={"quantity": quantity},
        )

        if not created:
            if inventory.quantity < basket_item.quantity:
                return Response(
                    {"error": "Not enough items in stock 162"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            basket_item.quantity += int(quantity)
            basket_item.save()
        inventory.quantity -= int(quantity)
        for img in item.images.all():
            basket_item.images.add(img)
        basket_item.save()
        inventory.save()

        serializer = self.get_serializer(basket_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(
        summary="List categories",
        description="Retrieve a list of categories.",
        responses={200: CategorySerializer(many=True)},
    ),
)
class CategoryModelViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CategoryDetailSerializer
        else:
            return self.serializer_class


@extend_schema_view(
    create=extend_schema(
        request=OrderSerializer,
        summary="Create an order",
        description="Create a new order for the user,"
                    " including delivery address and items from the basket.",
        responses={201: OrderSerializer},
    ),
)
class OrderModelViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Order.objects.filter(user=user)

    @transaction.atomic
    def create(self, request, *args):
        user = self.request.user
        basket = self.get_basket_for_user(user)
        delivery_info = {
            "delivery_address": request.data.get("delivery_info.delivery_address"),
            "full_name": request.data.get("delivery_info.full_name"),
            "post_department": request.data.get("delivery_info.post_department"),
            "number": request.data.get("delivery_info.number"),
            "email": request.data.get("delivery_info.email"),
            "comments": request.data.get("delivery_info.comments"),
        }
        payment_type = request.data.get("payment_type")
        if payment_type not in ["card", "cash_on_delivery"]:
            return Response(
                {"error": "Invalid payment type"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            print("order create")
            order = self.create_order(user, payment_type)
            print("order created")
            print("delivery_info create")
            self.create_delivery_info(delivery_info, order.id)
            print("delivery_info created")
            print("order items create")
            self.create_order_items(basket, order)
            print("order items created")

            if payment_type == "card":
                checkout_url = self.create_checkout_session(order.id)
                order.checkout_url = checkout_url
                order.save()

                serializer = self.get_serializer(order)
                response_data = serializer.data
                response_data["checkout_url"] = checkout_url
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                order.is_paid = False
                order.save()
                self.delete_basket(user)

                serializer = self.get_serializer(order)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def create_delivery_info(self, delivery_info: dict, order_id: int) -> DeliveryInfo:
        try:
            order = Order.objects.get(id=order_id)
            print(f"Order found: {order}")
            delivery_info_obj = DeliveryInfo.objects.create(
                delivery_address=delivery_info["delivery_address"],
                full_name=delivery_info["full_name"],
                post_department=delivery_info["post_department"],
                number=delivery_info["number"],
                email=delivery_info["email"],
                comments=delivery_info["comments"],
                order=order,
            )
            return delivery_info_obj
        except Order.DoesNotExist:
            print(f"Order with id {order_id} does not exist.")
            raise
        except Exception as e:
            print(f"An error occurred while creating DeliveryInfo: {str(e)}")
            raise

    def create_order(self, user, payment_type):
        return Order.objects.create(user=user, payment_type=payment_type)

    def create_checkout_session(self, order_id):
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            order = Order.objects.get(id=order_id)
            items = order.items.all()

            line_items = []
            for item in items:
                line_items.append({
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': item.item.name,
                        },
                        'unit_amount': int(item.price * 100),
                    },
                    'quantity': item.quantity,
                })

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url='https://inst-store-api.onrender.com/success.html',
                cancel_url='https://inst-store-api.onrender.com/cancel.html',
                metadata={
                    'order_id': order_id,
                }
            )
            return checkout_session.url
        except Exception as e:
            raise ValueError(f"Failed to create checkout session: {str(e)}")

    def create_order_items(self, basket: Basket, order: Order):
        for basket_item in basket.basket_items.all():
            item = Item.objects.get(id=basket_item.item.id)
            inventory = ItemInventory.objects.get(
                item=basket_item.item, size=basket_item.size, color=basket_item.color
            )
            if inventory.quantity < basket_item.quantity:
                raise ValueError("Not enough items in stock")

            inventory.quantity -= basket_item.quantity
            inventory.save()

            OrderItem.objects.create(
                order=order,
                item=basket_item.item,
                price=item.price,
                size=basket_item.size,
                color=basket_item.color,
                quantity=basket_item.quantity,
            )

    def get_basket_for_user(self, user: User) -> Basket:
        return Basket.objects.get(user=user)

    @staticmethod
    def delete_basket(user) -> None:
        try:
            basket = Basket.objects.get(user=user)
            basket.delete()
        except Basket.DoesNotExist:
            print(f"No basket found for user {user}")
        except Exception as e:
            print(f"Unexpected error during basket deletion: {e}")


@csrf_exempt
def stripe_webhook(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    payload = request.body.decode("utf-8")
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)
    except Exception as e:
        return HttpResponse(status=500)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        mark_order_complete(session)
    return HttpResponse(status=200)


def mark_order_complete(event: dict) -> None:
    order_id = event["metadata"]["order_id"]
    order = Order.objects.get(id=order_id)
    user = order.user
    print(f"Order before marking as paid: {order.is_paid}")
    order.is_paid = True
    try:
        print(f"Attempting to save order {order.id} with is_paid=True")
        order.save()
        print(f"Order {order.id} marked as paid: {order.is_paid}")
    except Exception as e:
        print(f"Error saving order: {e}")
    OrderModelViewSet.delete_basket(user)
