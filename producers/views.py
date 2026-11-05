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
        
        if getattr(user, 'role', None) == 'superadmin' or user.is_superuser:
            tenant_id = self.request.headers.get('X-Tenant-ID') or self.request.query_params.get('tenant')
            if tenant_id and str(tenant_id).lower() not in ('all', 'undefined', 'null', ''):
                try:
                    queryset = queryset.filter(tenant_id=int(tenant_id))
                except (ValueError, TypeError):
                    queryset = queryset.filter(tenant_id=tenant_id)
            return queryset
        
        return queryset.filter(tenant=user.tenant)
    
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

    @action(detail=False, methods=['get'], url_path='clp-consumed-weight')
    def clp_consumed_weight(self, request):
        """
        Calcula el peso neto consumido en kg para un CLP y productor específico
        en las recepciones principales registradas dentro de la campaña activa.
        Excluye descartes (los cuales no descuentan cupo SENASA).
        """
        import json
        from decimal import Decimal
        from reports.models import Report
        from .serializers import parse_decimal_kg

        clp_code = (request.query_params.get('clp') or '').strip()
        if not clp_code:
            return Response(
                {'error': 'El parámetro clp es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        producer_id = request.query_params.get('producer_id')
        producer_code = (request.query_params.get('producer_code') or '').strip()
        total_kg_param = request.query_params.get('total_kg')

        producer = None
        if producer_id and str(producer_id).isdigit():
            producer = Producer.objects.filter(id=int(producer_id)).first()
        elif producer_code:
            producer = Producer.objects.filter(code__iexact=producer_code).first()

        # Determinar el tenant (sede)
        user = request.user
        tenant = None
        if getattr(user, 'role', None) == 'superadmin' or user.is_superuser:
            tenant_id = request.headers.get('X-Tenant-ID') or request.query_params.get('tenant')
            if tenant_id and str(tenant_id).lower() not in ('all', 'undefined', 'null', ''):
                from tenants.models import Tenant
                try:
                    tenant = Tenant.objects.filter(id=int(tenant_id)).first()
                except (ValueError, TypeError):
                    pass
            elif producer and producer.tenant:
                tenant = producer.tenant
        else:
            tenant = getattr(user, 'tenant', None)

        reports_qs = Report.objects.all()
        if tenant:
            reports_qs = reports_qs.filter(tenant=tenant)

        # Filtrar recepciones de la campaña activa
        reports_qs = reports_qs.filter(campaign__status='active')

        # Excluir descartes
        reports_qs = reports_qs.exclude(
            lote__startswith='DESC-'
        ).exclude(
            datosGenerales_json__icontains='"reporteOrigenId"'
        ).exclude(
            datosGenerales_json__icontains='"tipoReporte": "descarte"'
        ).exclude(
            datosGenerales_json__icontains='"tipoReporte":"descarte"'
        )

        # Filtro en base de datos preliminar
        reports_qs = reports_qs.filter(datosGenerales_json__icontains=clp_code)

        consumed_kg = Decimal('0')
        receptions_count = 0
        campaign_names = set()
        matched_reports = []

        target_clp_clean = clp_code.upper()

        for report in reports_qs:
            try:
                dg = json.loads(report.datosGenerales_json or '{}')
            except Exception:
                dg = {}

            # Verificación estricta de código CLP
            report_clp = (dg.get('clp') or dg.get('codigoClp') or '').strip().upper()
            if report_clp != target_clp_clean:
                continue

            # Validación opcional de productor si se especificó
            if producer:
                prod_code = str(dg.get('productorCode') or dg.get('codigoProductor') or '').strip().upper()
                prod_name = str(dg.get('productor') or '').strip().upper()
                if prod_code and producer.code and prod_code != str(producer.code).strip().upper():
                    continue
                elif not prod_code and producer.name and prod_name and prod_name != str(producer.name).strip().upper():
                    continue

            peso_neto = report.totalPesoNeto or Decimal('0')
            consumed_kg += Decimal(str(peso_neto))
            receptions_count += 1
            if report.campaign and report.campaign.name:
                campaign_names.add(report.campaign.name)

            matched_reports.append({
                'id': report.id,
                'lote': report.lote,
                'fecha': dg.get('fecha'),
                'peso_neto': float(peso_neto),
                'campaign': report.campaign.name if report.campaign else None
            })

        campaign_name_str = ', '.join(sorted(campaign_names)) if campaign_names else None

        data = {
            'clp': clp_code,
            'consumed_kg': float(consumed_kg),
            'receptions_count': receptions_count,
            'campaign_names': list(campaign_names),
            'campaign_name': campaign_name_str,
            'reports': matched_reports
        }

        if total_kg_param is not None and str(total_kg_param).strip() != '':
            total_val = parse_decimal_kg(total_kg_param)
            suggested_saldo = max(Decimal('0'), total_val - consumed_kg)
            data['total_kg'] = float(total_val)
            data['suggested_saldo_kg'] = float(suggested_saldo)

        return Response(data)

    @action(detail=False, methods=['get'], url_path='clp_consumed_weight')
    def clp_consumed_weight_underscore(self, request):
        """Alias para soportar llamadas con guión bajo"""
        return self.clp_consumed_weight(request)


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

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return queryset.none()

        if getattr(user, 'role', None) == 'superadmin' or user.is_superuser:
            tenant_id = self.request.headers.get('X-Tenant-ID') or self.request.query_params.get('tenant')
            if tenant_id and str(tenant_id).lower() not in ('all', 'undefined', 'null', ''):
                try:
                    queryset = queryset.filter(producer__tenant_id=int(tenant_id))
                except (ValueError, TypeError):
                    queryset = queryset.filter(producer__tenant_id=tenant_id)
            return queryset

        return queryset.filter(producer__tenant=user.tenant)

    @action(detail=False, methods=['get'])
    def all(self, request):
        """Obtener todos los CLPs activos sin paginación"""
        queryset = self.filter_queryset(self.get_queryset().filter(is_active=True))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

