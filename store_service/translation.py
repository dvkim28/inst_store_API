from modeltranslation.translator import TranslationOptions, register

from .models import Category, Item, ItemColor, ItemDescription, ItemSize


@register(Item)
class ItemTranslationOptions(TranslationOptions):
    fields = ("name", "fabric")


@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ("name", "description")


@register(ItemDescription)
class ItemDescriptionTranslationOptions(TranslationOptions):
    fields = ("title", "description")


@register(ItemColor)
class ItemColorTranslationOptions(TranslationOptions):
    fields = ("color",)
