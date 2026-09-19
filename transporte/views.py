from rest_framework import viewsets, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from .models import TransportCompany, Driver, Vehicle
from .serializers import TransportCompanySerializer, DriverSerializer, VehicleSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class TransportCompanyViewSet(viewsets.ModelViewSet):
    """CRUD ViewSet para Empresas de Transporte"""
    queryset = TransportCompany.objects.all().prefetch_related('drivers', 'vehicles')
    serializer_class = TransportCompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tenant', 'is_active', 'ruc']
    search_fields = ['ruc', 'razon_social', 'phone', 'address']
    ordering_fields = ['razon_social', 'ruc', 'created_at']
    ordering = ['razon_social']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return queryset.none()

        if user.role == 'superadmin' or user.is_superuser:
            tenant_id = self.request.query_params.get('tenant')
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            return queryset

        if user.tenant:
            queryset = queryset.filter(tenant=user.tenant)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'superadmin' or user.is_superuser:
            if serializer.validated_data.get('tenant'):
                serializer.save()
            else:
                serializer.save(tenant=user.tenant)
        else:
            serializer.save(tenant=user.tenant)

    @action(detail=False, methods=['get'])
    def all(self, request):
        """Devuelve todas las empresas activas con sus choferes y vehículos sin paginación"""
        queryset = self.filter_queryset(self.get_queryset().filter(is_active=True))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class DriverViewSet(viewsets.ModelViewSet):
    """CRUD ViewSet para Choferes"""
    queryset = Driver.objects.all().select_related('company')
    serializer_class = DriverSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['company', 'is_active']
    search_fields = ['name', 'license_number']
    ordering_fields = ['name', 'license_number', 'created_at']
    ordering = ['name']

    @action(detail=False, methods=['get'])
    def all(self, request):
        """Devuelve todos los choferes activos sin paginación"""
        queryset = self.filter_queryset(self.get_queryset().filter(is_active=True))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class VehicleViewSet(viewsets.ModelViewSet):
    """CRUD ViewSet para Vehículos"""
    queryset = Vehicle.objects.all().select_related('company')
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['company', 'is_active']
    search_fields = ['plate', 'brand_model']
    ordering_fields = ['plate', 'created_at']
    ordering = ['plate']

    @action(detail=False, methods=['get'])
    def all(self, request):
        """Devuelve todos los vehículos activos sin paginación"""
        queryset = self.filter_queryset(self.get_queryset().filter(is_active=True))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
