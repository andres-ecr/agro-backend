from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .models import Producer, ProducerCLP
from .serializers import ProducerSerializer, ProducerListSerializer, ProducerCLPSerializer
from rest_framework.permissions import IsAuthenticated

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProducerViewSet(viewsets.ModelViewSet):
    queryset = Producer.objects.all().prefetch_related('clp_list')
    serializer_class = ProducerSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['code', 'name', 'clp', 'tenant']
    search_fields = ['code', 'name', 'clp', 'clp_list__code']
    ordering_fields = ['code', 'name', 'created_at']
    ordering = ['code']
    permission_classes = [IsAuthenticated]
    
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
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProducerListSerializer
        return ProducerSerializer
    
    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'superadmin' or user.is_superuser:
            if serializer.validated_data.get('tenant'):
                serializer.save(created_by=user)
            else:
                serializer.save(created_by=user, tenant=user.tenant)
        else:
            serializer.save(created_by=user, tenant=user.tenant)
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        """
        Endpoint para obtener todos los productores sin paginación
        """
        queryset = self.filter_queryset(self.get_queryset())
        serializer = ProducerListSerializer(queryset, many=True)
        return Response(serializer.data)


class ProducerCLPViewSet(viewsets.ModelViewSet):
    """CRUD ViewSet para Códigos de Lugar de Producción (CLP)"""
    queryset = ProducerCLP.objects.all().select_related('producer')
    serializer_class = ProducerCLPSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['producer', 'is_active', 'code']
    search_fields = ['code', 'lugar_produccion', 'producer__name']
    ordering_fields = ['code', 'created_at']
    ordering = ['code']
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def all(self, request):
        """Obtener todos los CLPs activos sin paginación"""
        queryset = self.filter_queryset(self.get_queryset().filter(is_active=True))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

