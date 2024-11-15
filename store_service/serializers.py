from rest_framework import serializers

from user_service.serializers import UserSerializer

from .models import (
    Basket,
    BasketItem,
    Category,
    DeliveryInfo,
    DeliveryType,
    ImageItem,
    Item,
    ItemColor,
    ItemDescription,
    ItemInventory,
    ItemSize,
    Order,
    OrderItem,
    PaymentType,
    PostDepartment,
)


class AdditionalInfoSerializer(serializers.Serializer):
    size = serializers.SlugRelatedField(slug_field="size", read_only=True, many=True)
    color = serializers.SlugRelatedField(slug_field="color", read_only=True, many=True)


class ItemDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemDescription
        fields = ["title", "description"]


class ImageItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageItem
        fields = ["image"]


class ItemSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    description = ItemDescriptionSerializer(many=True, read_only=True)
    additional_info = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = [
            "id",
            "sale_price",
            "brand",
            "date_added",
            "fabric",
            "images",
            "name",
            "description",
            "price",
            "category",
            "sale",
            "in_stock",
            "additional_info",
        ]

    def get_images(self, obj):
        return [image.image.url for image in obj.images.all()]

    def get_in_stock(self, obj):
        return ItemInventory.objects.filter(item=obj, quantity__gt=0).exists()

    def get_additional_info(self, obj):
        inventory = ItemInventory.objects.filter(item=obj)
        additional_info_list = []
        for inv in inventory:
            additional_info_list.append(
                {
                    "size": inv.size.size,
                    "color": inv.color.color,
                    "amount": inv.quantity,
                }
            )

        return additional_info_list


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
            "additional_info",
        ]


class BasketItemSerializer(serializers.ModelSerializer):
    item = serializers.SlugRelatedField(slug_field="name", queryset=Item.objects.all())
    size = serializers.SlugRelatedField(
        slug_field="size", queryset=ItemSize.objects.all()
    )
    color = serializers.SlugRelatedField(
        slug_field="color", queryset=ItemColor.objects.all()
    )
    quantity = serializers.IntegerField()

    class Meta:
        model = BasketItem
        fields = ["id", "item", "size", "color", "quantity", "images"]

    def validate(self, data):
        item = data.get("item", self.instance.item if self.instance else None)
        size = data.get("size", self.instance.size if self.instance else None)
        color = data.get("color", self.instance.color if self.instance else None)
        quantity = data.get(
            "quantity", self.instance.quantity if self.instance else None
        )

        try:
            inventory = ItemInventory.objects.get(item=item, size=size, color=color)
        except ItemInventory.DoesNotExist:
            raise serializers.ValidationError(
                "This combination of item, size, and color does not exist in inventory."
            )

        if inventory.quantity < quantity:
            raise serializers.ValidationError("Not enough items in stock 129")

        return data


class BasketItemForBasketSerializer(serializers.ModelSerializer):
    item = serializers.SlugRelatedField(slug_field="name", read_only=True)
    size = serializers.SlugRelatedField(
        slug_field="size", queryset=ItemSize.objects.all()
    )
    color = serializers.SlugRelatedField(
        slug_field="color", queryset=ItemColor.objects.all()
    )
    quantity = serializers.IntegerField()
    images = ImageItemSerializer(many=True, read_only=True, source="item.images")

    class Meta:
        model = BasketItem
        fields = ["id", "item", "size", "color", "price", "quantity", "images"]


class BasketSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    basket_items = BasketItemForBasketSerializer(many=True, read_only=True)

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
    size = serializers.SlugRelatedField(slug_field="size", read_only=True)
    color = serializers.SlugRelatedField(slug_field="color", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["item", "price", "size", "color", "quantity"]


class PostDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostDepartment
        fields = "__all__"


class DeliveryInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryInfo
        fields = ("full_name", "number", "email", "comments")


class DeliveryInfoDetailSerializer(DeliveryInfoSerializer):
    class Meta:
        model = DeliveryInfo
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payment_type = serializers.ChoiceField(choices=PaymentType.choices)
    delivery_info = DeliveryInfoDetailSerializer(many=False, read_only=False)
    post_department = PostDepartmentSerializer(many=False, read_only=False)

    class Meta:
        model = Order
        fields = [
            "id",
            "items",
            "payment_type",
            "delivery_info",
            "post_department",
        ]
