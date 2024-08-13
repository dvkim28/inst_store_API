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
)


class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "category")
    filter_horizontal = ("images",)


class ImageItemAdmin(admin.ModelAdmin):
    list_display = ("image",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1  # Количество пустых форм для добавления новых записей


class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "delivery_address", "created_at", "is_paid")
    inlines = [OrderItemInline]


admin.site.register(Order, OrderAdmin)

admin.site.register(Item, ItemAdmin)
admin.site.register(ImageItem, ImageItemAdmin)
admin.site.register(ItemColor)
admin.site.register(Category)
admin.site.register(ItemSize)
admin.site.register(Basket)
