# reports/views.py
from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from .models import Report
from .serializers import ReportSerializer, ReportListSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
import json
from django.db.models import Sum, Avg, Count, Q
from django.utils.dateparse import parse_date
from decimal import Decimal

class ReportFilter(django_filters.FilterSet):
    """Filtros personalizados para reportes"""
    fecha_desde = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    fecha_hasta = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    lote = django_filters.CharFilter(field_name='lote', lookup_expr='icontains')
    producto = django_filters.CharFilter(field_name='producto', lookup_expr='iexact')
    productor = django_filters.CharFilter(method='filter_productor')
    placa = django_filters.CharFilter(method='filter_placa')
    licencia = django_filters.CharFilter(method='filter_licencia')
    
    def filter_productor(self, queryset, name, value):
        """Filtrar por productor (búsqueda parcial en datosGenerales_json)"""
        # Buscar el valor de forma parcial e insensible a mayúsculas/minúsculas
        # Esto buscará cualquier ocurrencia del valor en el JSON
        return queryset.filter(datosGenerales_json__icontains=value.upper())
    
    def filter_placa(self, queryset, name, value):
        """Filtrar por placa (búsqueda parcial en datosGenerales_json)"""
        # Buscar el valor de forma parcial e insensible a mayúsculas/minúsculas
        return queryset.filter(datosGenerales_json__icontains=value.upper())
    
    def filter_licencia(self, queryset, name, value):
        """Filtrar por licencia (búsqueda parcial en datosGenerales_json)"""
        # Buscar el valor de forma parcial e insensible a mayúsculas/minúsculas
        return queryset.filter(datosGenerales_json__icontains=value.upper())
    
    class Meta:
        model = Report
        fields = ['fecha_desde', 'fecha_hasta', 'lote', 'producto', 'productor', 'placa', 'licencia']

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ReportFilter
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
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Obtener resumen estadístico de los reportes, aplicando los mismos filtros
        que se pueden aplicar a la lista de reportes.
        """
        # Aplicar los mismos filtros que se aplican a la lista
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calcular estadísticas
        stats = queryset.aggregate(
            total_reportes=Count('id'),
            total_peso_neto=Sum('totalPesoNeto'),
            total_jabas=Sum('totalJabas'),
        )
        
        # Calcular promedio por reporte
        if stats['total_reportes'] > 0 and stats['total_peso_neto'] is not None:
            promedio_reporte = stats['total_peso_neto'] / stats['total_reportes']
            # Redondear a 1 decimal
            promedio_reporte = round(promedio_reporte, 1)
        else:
            promedio_reporte = 0
        
        # Asegurar que los valores no sean None
        stats['total_reportes'] = stats['total_reportes'] or 0
        stats['total_peso_neto'] = float(stats['total_peso_neto'] or 0)
        stats['total_jabas'] = stats['total_jabas'] or 0
        stats['promedio_reporte'] = float(promedio_reporte)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def test_filters(self, request):
        """
        Endpoint de prueba para verificar que los filtros funcionan correctamente
        """
        # Obtener algunos reportes de ejemplo para mostrar la estructura
        sample_reports = Report.objects.all()[:3]
        
        sample_data = []
        for report in sample_reports:
            try:
                datos_generales = json.loads(report.datosGenerales_json) if report.datosGenerales_json else {}
                sample_data.append({
                    'id': report.id,
                    'producto': report.producto,
                    'lote': report.lote,
                    'datos_generales': datos_generales
                })
            except json.JSONDecodeError:
                sample_data.append({
                    'id': report.id,
                    'producto': report.producto,
                    'lote': report.lote,
                    'datos_generales_raw': report.datosGenerales_json
                })
        
        return Response({
            'message': 'Datos de ejemplo para verificar filtros',
            'sample_reports': sample_data,
            'available_filters': [
                'fecha_desde (YYYY-MM-DD)',
                'fecha_hasta (YYYY-MM-DD)', 
                'lote (búsqueda parcial)',
                'producto (coincidencia exacta)',
                'productor (búsqueda parcial)',
                'placa (búsqueda parcial)',
                'licencia (búsqueda parcial)'
            ]
        })
    
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
