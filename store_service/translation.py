from modeltranslation.translator import register, TranslationOptions
from .models import Item, Category, ItemDescription, ItemSize, ItemColor

@register(Item)
class ItemTranslationOptions(TranslationOptions):
    fields = ('name', 'fabric')

@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

@register(ItemDescription)
class ItemDescriptionTranslationOptions(TranslationOptions):
    fields = ('title', 'description')


@register(ItemColor)
class ItemColorTranslationOptions(TranslationOptions):
    fields = ('color',)
