from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .models import Producer
from .serializers import ProducerSerializer, ProducerListSerializer
from rest_framework.permissions import IsAuthenticated

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProducerViewSet(viewsets.ModelViewSet):
    queryset = Producer.objects.all()
    serializer_class = ProducerSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['code', 'name', 'clp']
    search_fields = ['code', 'name', 'clp']
    ordering_fields = ['code', 'name', 'created_at']
    ordering = ['code']
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProducerListSerializer
        return ProducerSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        """
        Endpoint para obtener todos los productores sin paginación
        """
        queryset = self.filter_queryset(self.get_queryset())
        serializer = ProducerListSerializer(queryset, many=True)
        return Response(serializer.data)
