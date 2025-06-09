from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProducerViewSet

router = DefaultRouter()
router.register('', ProducerViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
