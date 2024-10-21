import os

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import DecimalField, Sum

from .utils import (
    translate_and_update_category,
    translate_and_update_item,
    translate_and_update_description,
)


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not is_new:
            old_category = Category.objects.get(pk=self.pk)
            old_name = old_category.name
            old_description = old_category.description
        else:
            old_name = None

        super().save(*args, **kwargs)

        if is_new or old_name != self.name or old_description != self.description:
            translate_and_update_category.delay(self.pk)


def item_upload_path(instance, filename) -> str:
    _, ext = os.path.splitext(filename)
    return os.path.join("items", f"{instance.id}{ext}")


class ImageItem(models.Model):
    item = models.ForeignKey("Item", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=item_upload_path, null=True, blank=True)


class Item(models.Model):
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True, null=True)
    fabric = models.CharField(max_length=100, blank=True, null=True)
    price = DecimalField(max_digits=9, decimal_places=2)
    sale_price = DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="items"
    )
    size = models.ManyToManyField("ItemSize", related_name="items")
    color = models.ManyToManyField("ItemColor", related_name="items")
    sale = models.BooleanField(default=False)
    date_added = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if not is_new:
            try:
                old_item = Item.objects.get(pk=self.pk)
                old_name = old_item.name
                old_fabric = old_item.fabric
                old_descriptions = list(old_item.description.all())
            except ObjectDoesNotExist:
                old_name = None
                old_fabric = None
                old_descriptions = []
        else:
            old_name = None
            old_fabric = None
            old_descriptions = []

        super().save(*args, **kwargs)
        if (
            is_new
            or old_name != self.name
            or old_fabric != self.fabric
            or old_descriptions != list(self.description.all())
        ):
            translate_and_update_item(self.pk)

    def __str__(self):
        return self.name

    def total_stock(self):
        return self.inventory.aggregate(total=Sum("quantity"))["total"] or 0

    def is_in_stock(self):
        return self.total_stock() > 0


class ItemSize(models.Model):
    size = models.CharField(max_length=100)

    def __str__(self):
        return self.size


class ItemColor(models.Model):
    color = models.CharField(max_length=100)

    def __str__(self):
        return self.color


class ItemInventory(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="inventory")
    size = models.ForeignKey(
        ItemSize, on_delete=models.CASCADE, related_name="inventory"
    )
    color = models.ForeignKey(
        ItemColor, on_delete=models.CASCADE, related_name="inventory"
    )
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=9, decimal_places=2)

    class Meta:
        unique_together = ["item", "size", "color"]

    def __str__(self):
        return f"{self.item.name} - {self.size.size} - {self.color.color} ({self.quantity})"


class ItemDescription(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="description")

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not is_new:
            old_desc = ItemDescription.objects.get(pk=self.pk)
            old_desc_title = old_desc.title
            old_desc_description = old_desc.description
        else:
            old_desc_title = None
            old_desc_description = None

        super().save(*args, **kwargs)

        if (
            is_new
            or old_desc_title != self.title
            or old_desc_description != self.description
        ):
            translate_and_update_description.delay(self.pk)


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
    images = models.ManyToManyField(ImageItem, related_name="basket_items", blank=True)

    class Meta:
        unique_together = ["basket", "item", "size", "color"]


class Order(models.Model):
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="orders"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    checkout_url = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Order: {self.user}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
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
