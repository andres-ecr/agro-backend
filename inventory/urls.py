from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, WarehouseViewSet, InventoryItemViewSet, InventoryMovementViewSet

router = DefaultRouter()
router.register('products', ProductViewSet)
router.register('warehouses', WarehouseViewSet)
router.register('items', InventoryItemViewSet)
router.register('movements', InventoryMovementViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
