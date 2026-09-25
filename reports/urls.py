from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReportViewSet, ResponsableViewSet

router = DefaultRouter()
router.register('responsables', ResponsableViewSet, basename='responsable')
router.register('', ReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
    path('summary/', ReportViewSet.as_view({'get': 'summary'}), name='report-summary'),
]
