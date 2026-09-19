from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransportCompanyViewSet, DriverViewSet, VehicleViewSet

router = DefaultRouter()
router.register('companies', TransportCompanyViewSet, basename='transport-company')
router.register('drivers', DriverViewSet, basename='driver')
router.register('vehicles', VehicleViewSet, basename='vehicle')
router.register('', TransportCompanyViewSet, basename='transport-company-root')

urlpatterns = [
    path('', include(router.urls)),
]
