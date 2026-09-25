# reports/views.py
from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from .models import Report, Responsable
from .serializers import ReportSerializer, ReportListSerializer, ResponsableSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
import json
from django.db.models import Sum, Avg, Count, Q
from django.utils.dateparse import parse_date
from django.utils import timezone
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
    carga = django_filters.CharFilter(method='filter_carga')
    clp = django_filters.CharFilter(method='filter_clp')
    tenant = django_filters.CharFilter(method='filter_tenant')
    
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
    
    def filter_carga(self, queryset, name, value):
        """Filtrar por carga (búsqueda parcial en datosGenerales_json)"""
        return queryset.filter(datosGenerales_json__icontains=value)
    
    def filter_clp(self, queryset, name, value):
        """Filtrar por clp (búsqueda parcial en datosGenerales_json)"""
        return queryset.filter(datosGenerales_json__icontains=value)

    def filter_tenant(self, queryset, name, value):
        """Filtrar por tenant (ID numérico o ignorar si es 'all')"""
        if not value or str(value).lower() in ('all', 'undefined', 'null'):
            return queryset
        return queryset.filter(tenant_id=value)
    
    class Meta:
        model = Report
        fields = ['fecha_desde', 'fecha_hasta', 'lote', 'producto', 'productor', 'placa', 'licencia', 'carga', 'clp', 'tenant']

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
    
    def get_queryset(self):
        queryset = Report.objects.all()
        user = self.request.user
        if not user or not user.is_authenticated:
            return queryset.none()

        # Platform superadmin / is_superuser
        if getattr(user, 'role', None) == 'superadmin' or user.is_superuser:
            tenant_id = self.request.headers.get('X-Tenant-ID') or self.request.query_params.get('tenant')
            if tenant_id and str(tenant_id).lower() not in ('all', 'undefined', 'null', ''):
                try:
                    queryset = queryset.filter(tenant_id=int(tenant_id))
                except (ValueError, TypeError):
                    queryset = queryset.filter(tenant_id=tenant_id)
            return queryset

        # Plant admin or operator: strictly filter by user.tenant (cannot be overridden by header)
        return queryset.filter(tenant=user.tenant)
    
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
        user = self.request.user
        tenant = getattr(user, 'tenant', None)
        if (getattr(user, 'role', None) == 'superadmin' or user.is_superuser) and not tenant:
            tenant_id = self.request.headers.get('X-Tenant-ID') or self.request.query_params.get('tenant')
            if tenant_id and str(tenant_id).lower() not in ('all', 'undefined', 'null', ''):
                from tenants.models import Tenant
                tenant = Tenant.objects.filter(id=tenant_id).first()

        serializer.save(
            created_by=user,
            tenant=tenant
        )
    
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
    def dashboard_metrics(self, request):
        """
        Dashboard metrics with optional filtering by year, month, day, clp, and transportista:
        - Totales hoy / filtrados: kilos_hoy, jabas_hoy, cargas_hoy, filtered_kilos, etc.
        - Totales globales: total_kilos, total_jabas, total_cargas
        - Desglose por producto del queryset activo
        - Últimas recepciones del queryset activo
        """
        queryset = self.get_queryset()

        # Query filters
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        day = request.query_params.get('day')
        clp = request.query_params.get('clp')
        transportista = request.query_params.get('transportista')

        filtered_qs = queryset
        active_filters = {}

        if year and str(year).isdigit():
            filtered_qs = filtered_qs.filter(created_at__year=int(year))
            active_filters['year'] = int(year)
        if month and str(month).isdigit():
            filtered_qs = filtered_qs.filter(created_at__month=int(month))
            active_filters['month'] = int(month)
        if day and str(day).isdigit():
            filtered_qs = filtered_qs.filter(created_at__day=int(day))
            active_filters['day'] = int(day)
        if clp and str(clp).strip():
            clp_val = str(clp).strip()
            filtered_qs = filtered_qs.filter(datosGenerales_json__icontains=clp_val)
            active_filters['clp'] = clp_val
        if transportista and str(transportista).strip():
            trans_val = str(transportista).strip()
            filtered_qs = filtered_qs.filter(datosGenerales_json__icontains=trans_val)
            active_filters['transportista'] = trans_val

        is_filtered = bool(active_filters)

        today = timezone.localdate()
        today_qs = queryset.filter(created_at__date=today)

        today_stats = today_qs.aggregate(
            kilos_hoy=Sum('totalPesoNeto'),
            jabas_hoy=Sum('totalJabas'),
            cargas_hoy=Count('id')
        )

        total_stats = queryset.aggregate(
            total_kilos=Sum('totalPesoNeto'),
            total_jabas=Sum('totalJabas'),
            total_cargas=Count('id')
        )

        filtered_stats = filtered_qs.aggregate(
            filtered_kilos=Sum('totalPesoNeto'),
            filtered_jabas=Sum('totalJabas'),
            filtered_cargas=Count('id')
        )

        by_product = [
            {
                'producto': item['producto'],
                'kilos': float(item['kilos'] or 0),
                'jabas': item['jabas'] or 0,
                'cargas': item['cargas'] or 0,
            }
            for item in filtered_qs.values('producto').annotate(
                kilos=Sum('totalPesoNeto'),
                jabas=Sum('totalJabas'),
                cargas=Count('id')
            ).order_by('-kilos')
        ]

        recent_reports = filtered_qs.order_by('-created_at')[:5]
        recent_serialized = ReportListSerializer(recent_reports, many=True).data

        return Response({
            'is_filtered': is_filtered,
            'active_filters': active_filters,
            'kilos_hoy': float(today_stats['kilos_hoy'] or 0),
            'jabas_hoy': today_stats['jabas_hoy'] or 0,
            'cargas_hoy': today_stats['cargas_hoy'] or 0,
            'filtered_kilos': float(filtered_stats['filtered_kilos'] or 0),
            'filtered_jabas': filtered_stats['filtered_jabas'] or 0,
            'filtered_cargas': filtered_stats['filtered_cargas'] or 0,
            'total_kilos': float(total_stats['total_kilos'] or 0),
            'total_jabas': total_stats['total_jabas'] or 0,
            'total_cargas': total_stats['total_cargas'] or 0,
            'by_product': by_product,
            'recent_reports': recent_serialized,
        })
    
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


class ResponsableViewSet(viewsets.ModelViewSet):
    """CRUD ViewSet para Responsables de recepción (operarios que comparten PC)"""
    queryset = Responsable.objects.all()
    serializer_class = ResponsableSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return queryset.none()

        if getattr(user, 'role', None) == 'superadmin' or user.is_superuser:
            tenant_id = self.request.headers.get('X-Tenant-ID') or self.request.query_params.get('tenant')
            if tenant_id and str(tenant_id).lower() not in ('all', 'undefined', 'null', ''):
                try:
                    queryset = queryset.filter(tenant_id=int(tenant_id))
                except (ValueError, TypeError):
                    queryset = queryset.filter(tenant_id=tenant_id)
            return queryset.filter(is_active=True)

        return queryset.filter(tenant=user.tenant, is_active=True)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'superadmin' or user.is_superuser:
            tenant_id = self.request.headers.get('X-Tenant-ID') or self.request.query_params.get('tenant')
            if tenant_id and str(tenant_id).lower() not in ('all', 'undefined', 'null', ''):
                try:
                    tenant_id = int(tenant_id)
                except (ValueError, TypeError):
                    pass
                serializer.save(tenant_id=tenant_id)
                return
        serializer.save(tenant=user.tenant)

