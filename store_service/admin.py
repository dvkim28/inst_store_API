from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
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

# Inline для описания товара
class ItemDescriptionInline(admin.TabularInline):
    model = ItemDescription
    extra = 1  # Показывает одну пустую форму для добавления нового описания

# Inline для изображений товара
class ImageItemInline(admin.TabularInline):
    model = ImageItem
    extra = 1  # Показывает одну пустую форму для добавления нового изображения

# Админская модель для товаров
@admin.register(Item)
class ItemAdmin(TranslationAdmin):
    list_display = ("name", "price", "category", "sale")
    list_filter = ("category", "sale")
    search_fields = ("name", "brand")
    inlines = [ItemDescriptionInline, ImageItemInline]  # Добавляем описание и изображения

# Админская модель для изображений
@admin.register(ImageItem)
class ImageItemAdmin(admin.ModelAdmin):
    list_display = ("id", "image",)
    search_fields = ("id",)

# Inline для элементов заказа
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

# Админская модель для заказов
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "delivery_address", "created_at", "is_paid")
    list_filter = ("is_paid", "created_at")
    search_fields = ("user__username", "delivery_address__address")
    inlines = [OrderItemInline]

# Админская модель для инвентаря
@admin.register(ItemInventory)
class ItemInventoryAdmin(admin.ModelAdmin):
    list_display = ('item', 'size', 'color', 'quantity')
    list_filter = ('item', 'size', 'color')
    search_fields = ('item__name', 'size__size', 'color__color')

# Админская модель для цветов
@admin.register(ItemColor)
class ItemColorAdmin(TranslationAdmin):
    list_display = ('color',)
    search_fields = ('color',)

# Админская модель для категорий
@admin.register(Category)
class CategoryAdmin(TranslationAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Админская модель для размеров
@admin.register(ItemSize)
class ItemSizeAdmin(admin.ModelAdmin):
    list_display = ('size',)
    search_fields = ('size',)
