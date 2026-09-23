from django.urls import path
from .views import LicenseStatusView, LicenseActivateView, LicenseSyncView

urlpatterns = [
    path('status/', LicenseStatusView.as_view(), name='license-status'),
    path('activate/', LicenseActivateView.as_view(), name='license-activate'),
    path('sync/', LicenseSyncView.as_view(), name='license-sync'),
]
