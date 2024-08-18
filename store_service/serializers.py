from rest_framework import serializers

from user_service.serializers import UserSerializer

from .models import (
    Basket, Category, ImageItem, Item, Order, OrderItem, BasketItem, ItemSize, ItemColor, ItemInventory, ItemDescription
)
from user_service.serializers import DeliveryAddressSerializer

class ItemDescription(serializers.ModelSerializer):
    class Meta:
        model = ItemDescription
        fields = ["title", "description"]


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
    in_stock = serializers.SerializerMethodField()
    description = ItemDescription(many=True, read_only=True)


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

    def get_in_stock(self, obj):
        return ItemInventory.objects.filter(item=obj, quantity__gt=0).exists()


class ItemDetailSerializer(ItemSerializer):
    class Meta:
        model = Item
        fields = [
            "id",
            "images",
            "name",
            "description",
            "price",
            "category",
            "date_added",
            "size",
            "color",
        ]


class BasketItemSerializer(serializers.ModelSerializer):
    item = serializers.SlugRelatedField(slug_field='name', queryset=Item.objects.all())
    size = serializers.SlugRelatedField(slug_field='size', queryset=ItemSize.objects.all())
    color = serializers.SlugRelatedField(slug_field='color', queryset=ItemColor.objects.all())
    quantity = serializers.IntegerField()

    class Meta:
        model = BasketItem
        fields = ['id', 'item', 'size', 'color', 'quantity', "price"]

    def validate(self, data):
        item = data['item']
        size = data['size']
        color = data['color']
        quantity = data['quantity']

        try:
            inventory = ItemInventory.objects.get(item=item, size=size, color=color)
        except ItemInventory.DoesNotExist:
            raise serializers.ValidationError('This combination of item, size, and color does not exist in inventory.')

        if inventory.quantity < quantity:
            raise serializers.ValidationError('Not enough items in stock.')

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


class CategoryDetailSerializer(CategorySerializer):
    items = ItemDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "description", "items"]



class OrderItemSerializer(serializers.ModelSerializer):
    item = serializers.SlugRelatedField(slug_field="name", read_only=True)
    size = serializers.SlugRelatedField(slug_field='size', read_only=True)
    color = serializers.SlugRelatedField(slug_field='color', read_only=True)

    class Meta:
        model = OrderItem
        fields = ["item", "price", "size", "color", "quantity"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    delivery_address = DeliveryAddressSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "user", "delivery_address", "items"]