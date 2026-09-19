from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantViewSet, OrganizationViewSet

router = DefaultRouter()
router.register('organizations', OrganizationViewSet, basename='organization')
router.register('', TenantViewSet, basename='tenant')

urlpatterns = [
    path('', include(router.urls)),
]
