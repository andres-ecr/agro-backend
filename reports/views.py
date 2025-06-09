# reports/views.py
from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from .models import Report
from .serializers import ReportSerializer, ReportListSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
import json

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['producto', 'lote', 'status']
    search_fields = ['producto', 'lote', 'datosGenerales_json']
    ordering_fields = ['created_at', 'producto', 'lote', 'totalPesoNeto']
    ordering = ['-created_at']
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ReportListSerializer
        return ReportSerializer
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            # Registrar el error para depuración
            print(f"Error en create: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        # Implementar la lógica para descargar el reporte como Excel
        # (Esta es una implementación básica, deberías adaptarla según tus necesidades)
        try:
            report = self.get_object()
            # Aquí iría la lógica para generar el archivo Excel
            # Por ahora, solo devolvemos los datos en JSON
            return Response(self.get_serializer(report).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)