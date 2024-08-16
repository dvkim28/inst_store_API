import stripe
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Basket, Category, Item, Order, OrderItem, BasketItem, ItemSize, ItemColor
from .serializers import (
    BasketSerializer,
    CategorySerializer,
    ItemDetailSerializer,
    ItemSerializer,
    OrderSerializer,
    BasketItemSerializer,
)

from user_service.models import User, DeliveryAddress

from config import settings
from .tasks import send_telegram_message

from .utils import create_checkout_session


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
        description="Create a new basket "
                    "for the current user and add items to it.",
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


class BasketItemViewSet(viewsets.ModelViewSet):
    serializer_class = BasketItemSerializer

    def get_queryset(self):
        user = self.request.user
        return BasketItem.objects.filter(basket__user=user)

    def create(self, request, *args, **kwargs):
        item = request.data["item"]
        size = request.data.get('size')
        color = request.data.get('color')
        quantity = request.data.get('quantity', 1)

        try:
            item = Item.objects.get(name=item)
            size = ItemSize.objects.get(size=size)
            color = ItemColor.objects.get(color=color)
        except Item.DoesNotExist or ItemSize.DoesNotExist or ItemColor.DoesNotExist:
            return Response({'error': 'Item, size, or color not found'}, status=status.HTTP_400_BAD_REQUEST)

        basket, created = Basket.objects.get_or_create(user=request.user)

        basket_item, created = BasketItem.objects.get_or_create(
            basket=basket,
            item=item,
            size=size,
            color=color,
            defaults={'quantity': quantity}
        )

        if not created:
            basket_item.quantity += int(quantity)
            basket_item.save()

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

    def create(self, request, *args):
        user = request.user
        basket = self.get_basket_for_user(user)
        delivery_address = self.get_delivery_address(user)
        try:
            order = self.create_order(user, delivery_address)
            self.create_order_items(basket, order)
            self.delete_basket(basket)
        except Exception as e:
            return Response({"error": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            checkout_url = create_checkout_session(order)
        except Exception as e:
            return Response({"error": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(order)
        response_data = serializer.data
        response_data["checkout_url"] = checkout_url
        return Response(response_data, status=status.HTTP_201_CREATED)

    def create_order_items(self, basket: Basket, order: Order):
        for order_item in basket.basket_items.all():
            OrderItem.objects.create(
                order=order,
                item=order_item.item,
                price=order_item.price,
                size=order_item.size,
                color=order_item.color,
                quantity=order_item.quantity,
            )
    def get_basket_for_user(self, user: User) -> Basket:
        basket = Basket.objects.get(user=user)
        return basket

    def delete_basket(self, basket) -> None:
        basket.delete()

    def get_delivery_address(self, user: User) -> str:
        return DeliveryAddress.objects.get(user=user)

    def create_order(
        self, user: User, delivery_address: DeliveryAddress
    ) -> Order:
        return (Order.objects.
                create(user=user, delivery_address=delivery_address))


@csrf_exempt
def stripe_webhook(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = (stripe.Webhook.
                 construct_event(payload, sig_header, endpoint_secret))
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        mark_order_complete(event)
    return HttpResponse(status=200)


def mark_order_complete(event: dict) -> None:
    session = event["data"]["object"]
    order_id = session["metadata"].get("order_id")
    send_telegram_message.delay(order_id)
    order = Order.objects.get(id=order_id)
    order.is_paid = True
    order.save()
