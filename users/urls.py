from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import UserViewSet, CustomTokenObtainPairView, ChangePasswordView, MeView

router = DefaultRouter()
router.register('users', UserViewSet, basename='users-plural')
router.register('', UserViewSet, basename='users')

urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('me/', MeView.as_view(), name='me'),
    path('', include(router.urls)),
]
