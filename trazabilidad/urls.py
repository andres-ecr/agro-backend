from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CampoViewSet, CosechaViewSet, LoteViewSet,
    LoteEventViewSet, LoteDocumentViewSet
)

router = DefaultRouter()
router.register('campos', CampoViewSet)
router.register('cosechas', CosechaViewSet)
router.register('lotes', LoteViewSet)
router.register('eventos', LoteEventViewSet)
router.register('documentos', LoteDocumentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
