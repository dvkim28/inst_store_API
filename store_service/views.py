import stripe
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from user_service.models import User

from .models import (
    Basket,
    BasketItem,
    Category,
    DeliveryInfo,
    Item,
    ItemColor,
    ItemInventory,
    ItemSize,
    Order,
    OrderItem, PostDepartment,
)
from .serializers import (
    BasketItemSerializer,
    BasketSerializer,
    CategoryDetailSerializer,
    CategorySerializer,
    ItemDetailSerializer,
    ItemSerializer,
    OrderSerializer,
)
from .utils import (
    send_email_order_created,
    send_email_to_user_about_order_success)


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
        description=""
                    "Create a new basket for the "
                    "current user and add items to it.",
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
        item_main = Item.objects.get(name=item)
        print(";get; done")
        try:
            item = Item.objects.get(name=item)
            print("item found")
            size = ItemSize.objects.get(size=size)
            print("size found")
            color = ItemColor.objects.get(color=color)
            print("color found")
            inventory = ItemInventory.objects.get(
                item=item,
                size=size,
                color=color
            )
            print("inventory found")

            if inventory.quantity < int(quantity):
                return Response(
                    {"error": "Not enough items in stock"},
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
            price=item_main.price,
            defaults={"price": item_main.price, "quantity": quantity},
        )
        if not created:
            basket_item.quantity += int(quantity)
            basket_item.save()

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
    def create(self, request, *args, **kwargs):

        user = self.request.user

        try:
            basket = self.get_basket_for_user(user)
        except Exception:
            return Response({
                "error": "Unable to retrieve basket"},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = request.data.get("delivery_info")
        delivery_info = {
            "full_name": data["full_name"],
            "number": data["number"],
            "email": data["email"],
            "comments": data["comments"],
            "delivery_type": data["delivery_type"],
        }

        post_data = request.data.get("post_department")
        print(post_data)
        post_department = {
            "city": post_data["city"],
            "state": post_data["state"],
            "address": post_data["address"],
        }

        if not delivery_info["full_name"] or not delivery_info["number"]:
            return Response(
                {"error": "Delivery information is incomplete"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if (not post_department["city"]
                or not post_department["state"]
                or not post_department["address"]):
            return Response({
                "error": "Post department data is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            p_data = self.create_post_department(post_department)

            order = self.create_order(
                user,
                request.data.get("payment_type"),
                p_data
            )

            self.create_delivery_info(delivery_info, order.id)

            self.create_order_items(basket, order)

            payment_type = request.data.get("payment_type")

            if payment_type == "card":
                checkout_url = self.prepare_checkout_session(order.id)
                order.checkout_url = checkout_url
                order.save()

                serializer = self.get_serializer(order)
                response_data = serializer.data
                response_data["checkout_url"] = checkout_url
                return Response(response_data, status=status.HTTP_201_CREATED)

            elif payment_type == "cash_on_delivery":
                checkout_url = self.prepare_checkout_session(order.id)
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
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED
                )

        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def create_post_department(self, post_department: dict) -> PostDepartment:
        try:
            return PostDepartment.objects.create(
                city=post_department["city"],
                state=post_department["state"],
                address=post_department["address"]
            )
        except KeyError as e:
            raise ValueError(f"Missing key in post_department: {e}")
        except Exception as e:
            raise ValueError(f"Error creating PostDepartment: {str(e)}")

    def create_order(
            self,
            user,
            payment_type,
            p_data: PostDepartment
    ) -> Order:
        try:
            return Order.objects.create(
                user=user,
                payment_type=payment_type,
                post_department=p_data
            )
        except Exception as e:
            raise ValueError(f"Error creating order: {str(e)}")

    def create_delivery_info(
            self,
            delivery_info: dict,
            order_id: int
    ) -> DeliveryInfo:
        try:
            order = Order.objects.get(id=order_id)
            return DeliveryInfo.objects.create(
                full_name=delivery_info["full_name"],
                number=delivery_info["number"],
                email=delivery_info["email"],
                comments=delivery_info["comments"],
                order=order,
            )
        except Order.DoesNotExist:
            raise ValueError(f"Order with id {order_id} does not exist.")
        except KeyError as e:
            raise ValueError(f"Missing key in delivery_info: {e}")
        except Exception as e:
            raise ValueError(f"Error creating delivery info: {str(e)}")

    def create_order_items(self, basket: Basket, order: Order):
        try:
            for basket_item in basket.basket_items.all():
                item = Item.objects.get(id=basket_item.item.id)
                inventory = ItemInventory.objects.get(
                    item=basket_item.item,
                    size=basket_item.size,
                    color=basket_item.color
                )
                if inventory.quantity < basket_item.quantity:
                    raise ValueError(
                        f"Not enough items in stock for {item.name}"
                    )

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
        except Exception as e:
            raise ValueError(f"Error creating order items: {str(e)}")

    @transaction.atomic
    def prepare_checkout_session(self, order_id):

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            raise ValueError(f"Order with id {order_id} does not exist.")
        except Exception as e:
            raise ValueError(
                f"Unexpected error while retrieving order: {str(e)}"
            )

        line_items = []
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
        except Exception as e:
            raise ValueError(f"Error setting up Stripe API key: {str(e)}")

        if order.payment_type == "card":
            try:
                items = order.items.all()
                for item in items:
                    line_items.append({
                        "price_data": {
                            "currency": "usd",
                            "product_data": {"name": item.item.name},
                            "unit_amount": int(item.price * 100),
                        },
                        "quantity": item.quantity,
                    })
            except Exception as e:
                raise ValueError(f"Error while preparing line items: {str(e)}")
        else:
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Delivery fee",
                        "description": "Delivery fee"
                    },
                    "unit_amount": 200,
                },
                "quantity": 1,

            })
        return self.create_checkout_session(line_items, order_id)

    def create_checkout_session(self, line_items: list, order_id):
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url="https://inst-store-api.onrender.com/success.html",
                cancel_url="https://inst-store-api.onrender.com/cancel.html",
                metadata={
                    "order_id": order_id,
                },
            )
            return checkout_session.url
        except Exception as e:
            raise ValueError(f"Failed to create checkout session: {str(e)}")

    def get_basket_for_user(self, user: User) -> Basket:
        try:
            return Basket.objects.get(user=user)
        except Basket.DoesNotExist:
            raise ValueError(f"No basket found for user {user}")
        except Exception as e:
            raise ValueError(f"Error retrieving basket: {str(e)}")

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
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            endpoint_secret
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    except Exception:
        return HttpResponse(status=500)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        mark_order_complete(session)
    return HttpResponse(status=200)


def mark_order_complete(event: dict) -> None:
    order_id = event["metadata"]["order_id"]
    order = Order.objects.get(id=order_id)
    user = order.user
    order.is_paid = True
    send_email_order_created(order, user)
    send_email_to_user_about_order_success(order, user)
    try:
        order.save()
    except Exception:
        OrderModelViewSet.delete_basket(user)
