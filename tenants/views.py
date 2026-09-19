from rest_framework import viewsets, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from users.permissions import IsSuperAdminUser
from .models import Tenant
from .serializers import TenantSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class TenantViewSet(viewsets.ModelViewSet):
    """API endpoint para gestionar Sedes / Tenants"""
    serializer_class = TenantSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'code']
    search_fields = ['name', 'code', 'ruc', 'address']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['name']

    def get_permissions(self):
        """Allow full CRUD for superadmin / is_superuser. Read-only for regular users."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsSuperAdminUser()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Tenant.objects.none()
        if user.role == 'superadmin' or user.is_superuser:
            return Tenant.objects.all().order_by('name')
        if user.tenant:
            return Tenant.objects.filter(id=user.tenant_id)
        return Tenant.objects.none()

    @action(detail=False, methods=['get'])
    def all(self, request):
        """Devuelve tenants activos sin paginación (para selectores de UI)"""
        queryset = self.filter_queryset(self.get_queryset().filter(is_active=True))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
