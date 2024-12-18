from django.urls import include, path
from rest_framework import routers

from .views import (
    BasketItemViewSet,
    BasketModelViewSet,
    CategoryModelViewSet,
    ItemModelViewSet,
    OrderModelViewSet,
)

router = routers.DefaultRouter()
router.register("items", ItemModelViewSet)
router.register("basket", BasketModelViewSet)
router.register("categories", CategoryModelViewSet)
router.register("orders", OrderModelViewSet)
router.register(r"basket-items", BasketItemViewSet, basename="basketitem")

urlpatterns = [
    path("", include(router.urls)),
]

app_name = "store_service"
