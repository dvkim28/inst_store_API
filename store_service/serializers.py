from rest_framework import serializers

from user_service.serializers import UserSerializer

from .models import Basket, Category, ImageItem, Item, Order, OrderItem, BasketItem, ItemSize, ItemColor
from user_service.serializers import DeliveryAddressSerializer


class ImageItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageItem
        fields = ["image"]


class ItemSerializer(serializers.ModelSerializer):
    size = serializers.SlugRelatedField(
        slug_field="size",
        read_only=True,
        many=True
    )
    color = serializers.SlugRelatedField(
        slug_field="color",
        read_only=True,
        many=True
    )
    images = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = [
            "id",
            "sale_price",
            "brand",
            "date_added",
            "images",
            "name",
            "description",
            "price",
            "category",
            "size",
            "color",
            "sale",
            "in_stock",
        ]

    def get_images(self, obj):
        return [image.image.url for image in obj.images.all()]


class ItemDetailSerializer(ItemSerializer):
    class Meta:
        model = Item
        fields = ["id",
                  "images",
                  "name",
                  "description",
                  "price",
                  "category",
                  "date_added",
                  "size"]


class BasketItemSerializer(serializers.ModelSerializer):
    item = serializers.SlugRelatedField(slug_field='name', queryset=Item.objects.all())
    size = serializers.SlugRelatedField(slug_field='size', queryset=ItemSize.objects.all())
    color = serializers.SlugRelatedField(slug_field='color', queryset=ItemColor.objects.all())
    quantity = serializers.IntegerField()

    class Meta:
        model = BasketItem
        fields = ['id', 'item', 'size', 'color', 'quantity']

    def validate(self, data):
        basket = self.context['request'].user.basket
        if BasketItem.objects.filter(
            basket=basket,
            item=data['item'],
            size=data['size'],
            color=data['color']
        ).exists():
            raise serializers.ValidationError('This item already exists in the basket with the selected size and color.')
        return data

class BasketSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    basket_items = BasketItemSerializer(many=True, read_only=True)

    class Meta:
        model = Basket
        fields = ["id", "user", "basket_items"]


class BasketListSerializer(BasketSerializer):
    items = ItemDetailSerializer(many=True, read_only=True)

    class Meta(BasketSerializer.Meta):
        fields = ["id", "user", "items"]




class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]


class OrderItemSerializer(serializers.ModelSerializer):
    item = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["item", "price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    delivery_address = DeliveryAddressSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "user", "delivery_address", "items"]
