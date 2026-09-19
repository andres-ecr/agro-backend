from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProducerViewSet, ProducerCLPViewSet

router = DefaultRouter()
router.register('clps', ProducerCLPViewSet, basename='producer-clp')
router.register('', ProducerViewSet, basename='producer')

urlpatterns = [
    path('', include(router.urls)),
]
