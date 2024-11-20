import os

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import DecimalField, OneToOneField, Sum


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name


class ImageItem(models.Model):
    item = models.ForeignKey(
        "Item",
        on_delete=models.CASCADE,
        related_name="images")
    image = models.ImageField(
        upload_to="item_upload_path",
        null=True,
        blank=True)


class Item(models.Model):
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True, null=True)
    fabric = models.CharField(max_length=100, blank=True, null=True)
    price = DecimalField(max_digits=9, decimal_places=2)
    sale_price = DecimalField(
        max_digits=9,
        decimal_places=2,
        null=True,
        blank=True
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="items"
    )
    size = models.ManyToManyField("ItemSize", related_name="items")
    color = models.ManyToManyField("ItemColor", related_name="items")
    sale = models.BooleanField(default=False)
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.name

    def total_stock(self):
        return self.inventory.aggregate(total=Sum("quantity"))["total"] or 0

    def is_in_stock(self):
        return self.total_stock() > 0


def item_upload_path(instance, filename) -> str:
    _, ext = os.path.splitext(filename)
    return os.path.join("items", f"{instance.id}{ext}")


class ItemSize(models.Model):
    size = models.CharField(max_length=100)

    def __str__(self):
        return self.size


class ItemColor(models.Model):
    color = models.CharField(max_length=100)

    def __str__(self):
        return self.color


class ItemInventory(models.Model):
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="inventory"
    )
    size = models.ForeignKey(
        ItemSize, on_delete=models.CASCADE, related_name="inventory"
    )
    color = models.ForeignKey(
        ItemColor, on_delete=models.CASCADE, related_name="inventory"
    )
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ["item", "size", "color"]

    def __str__(self):
        return (f"{self.item.name} -"
                f"{self.size.size} - "
                f"{self.color.color} "
                f"({self.quantity})"
                )


class ItemDescription(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="description"
    )


class Basket(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)

    def __str__(self):
        return f"basket for {self.user}"


class BasketItem(models.Model):
    basket = models.ForeignKey(
        Basket, on_delete=models.CASCADE, related_name="basket_items"
    )
    price = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    size = models.ForeignKey(ItemSize, on_delete=models.CASCADE)
    color = models.ForeignKey(ItemColor, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    images = models.ManyToManyField(
        ImageItem,
        related_name="basket_items",
        blank=True)

    class Meta:
        unique_together = ["basket", "item", "size", "color"]


class DeliveryType(models.TextChoices):
    NEW_POST = "new_post", "New Post"
    PICKUP = "pickup", "pickup"


class DeliveryInfo(models.Model):
    full_name = models.TextField(blank=True, null=True)
    number = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    order = OneToOneField(
        "Order",
        on_delete=models.CASCADE,
        related_name="delivery_info"
    )
    delivery_type = models.CharField(
        max_length=20,
        choices=DeliveryType.choices)


class PaymentType(models.TextChoices):
    CARD = "card", "By card"
    CASH_ON_DELIVERY = "cash_on_delivery", "Cash on delivery"


class PostDepartment(models.Model):
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    address = models.TextField()


class Order(models.Model):
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="orders"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    checkout_url = models.TextField(blank=True, null=True)
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices)
    post_department = models.ForeignKey(
        to=PostDepartment,
        on_delete=models.CASCADE)

    def __str__(self):
        return f"Order: {self.user}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    size = models.ForeignKey(
        ItemSize,
        on_delete=models.CASCADE,
        related_name="items_set",
        null=True,
        blank=True,
    )
    color = models.ForeignKey(
        ItemColor,
        on_delete=models.CASCADE,
        related_name="items_set",
        null=True,
        blank=True,
    )
    quantity = models.PositiveIntegerField(default=1)
