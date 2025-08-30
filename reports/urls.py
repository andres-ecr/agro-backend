from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReportViewSet

router = DefaultRouter()
router.register('', ReportViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('summary/', ReportViewSet.as_view({'get': 'summary'}), name='report-summary'),
]
