from django.contrib import admin
from .models import (
    Category,
    ImageItem,
    Item,
    ItemColor,
    ItemSize,
    Order,
    Basket,
    OrderItem,
    ItemInventory,
    ItemDescription
)

class ItemDescriptionInline(admin.TabularInline):
    model = ItemDescription
    extra = 1  # Показывает одну пустую форму для добавления нового описания

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "category", "sale")
    # filter_horizontal = ("images",)
    list_filter = ("category", "sale")
    search_fields = ("name", "brand")
    inlines = [ItemDescriptionInline]  # Добавляем ItemDescriptionInline

@admin.register(ImageItem)
class ImageItemAdmin(admin.ModelAdmin):
    list_display = ("id", "image",)
    search_fields = ("id",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "delivery_address", "created_at", "is_paid")
    list_filter = ("is_paid", "created_at")
    search_fields = ("user__username", "delivery_address__address")
    inlines = [OrderItemInline]


@admin.register(ItemInventory)
class ItemInventoryAdmin(admin.ModelAdmin):
    list_display = ('item', 'size', 'color', 'quantity')
    list_filter = ('item', 'size', 'color')
    search_fields = ('item__name', 'size__size', 'color__color')


@admin.register(ItemColor)
class ItemColorAdmin(admin.ModelAdmin):
    list_display = ('color',)
    search_fields = ('color',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ItemSize)
class ItemSizeAdmin(admin.ModelAdmin):
    list_display = ('size',)
    search_fields = ('size',)


@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username',)
