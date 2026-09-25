from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Warehouse, InventoryItem, InventoryMovement, Campaign
from .serializers import ProductSerializer, WarehouseSerializer, InventoryItemSerializer, InventoryMovementSerializer, CampaignSerializer
from users.permissions import IsOwnerOrAdmin, IsSupervisorUser


class ProductViewSet(viewsets.ModelViewSet):
    """Viewset for products"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product_type', 'unit', 'tenant']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['name']
    
    def get_permissions(self):
        """Set custom permissions for each action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsSupervisorUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]

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
        
        if getattr(user, 'tenant', None):
            return queryset.filter(tenant=user.tenant)
        
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, 'role', None) == 'superadmin' or user.is_superuser:
            tenant = serializer.validated_data.get('tenant')
            if not tenant:
                tenant_id = self.request.headers.get('X-Tenant-ID') or self.request.query_params.get('tenant')
                if tenant_id and str(tenant_id).lower() not in ('all', 'undefined', 'null', ''):
                    try:
                        from tenants.models import Tenant
                        tenant = Tenant.objects.filter(id=int(tenant_id)).first()
                    except (ValueError, TypeError):
                        pass
            if not tenant and getattr(user, 'tenant', None):
                tenant = user.tenant
            serializer.save(created_by=user, tenant=tenant)
        else:
            serializer.save(created_by=user, tenant=user.tenant)


class WarehouseViewSet(viewsets.ModelViewSet):
    """Viewset for warehouses"""
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['warehouse_type']
    search_fields = ['name', 'location', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_permissions(self):
        """Set custom permissions for each action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsSupervisorUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]


class InventoryItemViewSet(viewsets.ModelViewSet):
    """Viewset for inventory items"""
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'warehouse', 'status', 'lot_number']
    search_fields = ['product__name', 'product__code', 'lot_number']
    ordering_fields = ['product__name', 'quantity', 'expiration_date']
    ordering = ['product__name']
    
    def get_permissions(self):
        """Set custom permissions for each action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsSupervisorUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['POST'])
    def update_status(self, request, pk=None):
        """Update the status of an inventory item"""
        item = self.get_object()
        
        # Check if user has permission (supervisor or admin)
        self.check_object_permissions(request, item)
        
        # Get new status from request
        new_status = request.data.get('status')
        if not new_status or new_status not in dict(InventoryItem.STATUS_CHOICES):
            return Response(
                {"detail": "Invalid status."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update item status
        item.status = new_status
        item.save()
        
        serializer = self.get_serializer(item)
        return Response(serializer.data)


class InventoryMovementViewSet(viewsets.ModelViewSet):
    """Viewset for inventory movements"""
    queryset = InventoryMovement.objects.all()
    serializer_class = InventoryMovementSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['movement_type', 'product', 'source_warehouse', 'destination_warehouse', 'lot_number']
    search_fields = ['product__name', 'product__code', 'reference', 'notes']
    ordering_fields = ['timestamp', 'product__name']
    ordering = ['-timestamp']
    
    def get_permissions(self):
        """Set custom permissions for each action"""
        if self.action in ['create']:
            permission_classes = [permissions.IsAuthenticated, IsSupervisorUser]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def create(self, validated_data):
        """Create a new inventory movement and update inventory"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get validated data
        movement_type = serializer.validated_data.get('movement_type')
        product = serializer.validated_data.get('product')
        source_warehouse = serializer.validated_data.get('source_warehouse')
        destination_warehouse = serializer.validated_data.get('destination_warehouse')
        quantity = serializer.validated_data.get('quantity')
        lot_number = serializer.validated_data.get('lot_number')
        
        # Validate movement data
        if movement_type == InventoryMovement.TYPE_IN and not destination_warehouse:
            return Response(
                {"detail": "Destination warehouse is required for IN movements."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if movement_type == InventoryMovement.TYPE_OUT and not source_warehouse:
            return Response(
                {"detail": "Source warehouse is required for OUT movements."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if movement_type == InventoryMovement.TYPE_TRANSFER and (not source_warehouse or not destination_warehouse):
            return Response(
                {"detail": "Source and destination warehouses are required for TRANSFER movements."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the movement
        movement = serializer.save(created_by=self.request.user)
        
        # Update inventory based on movement type
        try:
            if movement_type == InventoryMovement.TYPE_IN:
                # Add to destination warehouse
                self._add_to_inventory(product, destination_warehouse, quantity, lot_number)
            
            elif movement_type == InventoryMovement.TYPE_OUT:
                # Remove from source warehouse
                self._remove_from_inventory(product, source_warehouse, quantity, lot_number)
            
            elif movement_type == InventoryMovement.TYPE_TRANSFER:
                # Remove from source and add to destination
                self._remove_from_inventory(product, source_warehouse, quantity, lot_number)
                self._add_to_inventory(product, destination_warehouse, quantity, lot_number)
            
            elif movement_type == InventoryMovement.TYPE_ADJUSTMENT:
                # Handle adjustment (could be positive or negative)
                if source_warehouse:
                    self._adjust_inventory(product, source_warehouse, -quantity, lot_number)
                if destination_warehouse:
                    self._adjust_inventory(product, destination_warehouse, quantity, lot_number)
        
        except Exception as e:
            # If inventory update fails, delete the movement and return error
            movement.delete()
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def _add_to_inventory(self, product, warehouse, quantity, lot_number):
        """Add quantity to inventory"""
        try:
            item, created = InventoryItem.objects.get_or_create(
                product=product,
                warehouse=warehouse,
                lot_number=lot_number or '',
                defaults={
                    'quantity': 0,
                    'created_by': self.request.user
                }
            )
            
            item.quantity += quantity
            item.save()
            
        except Exception as e:
            raise Exception(f"Error adding to inventory: {str(e)}")
    
    def _remove_from_inventory(self, product, warehouse, quantity, lot_number):
        """Remove quantity from inventory"""
        try:
            # Get the inventory item
            item = InventoryItem.objects.filter(
                product=product,
                warehouse=warehouse,
                lot_number=lot_number or ''
            ).first()
            
            if not item:
                raise Exception("Inventory item not found")
            
            if item.quantity < quantity:
                raise Exception("Insufficient quantity in inventory")
            
            item.quantity -= quantity
            item.save()
            
            # If quantity is zero, optionally delete the item
            if item.quantity == 0:
                item.delete()
            
        except Exception as e:
            raise Exception(f"Error removing from inventory: {str(e)}")
    
    def _adjust_inventory(self, product, warehouse, quantity, lot_number):
        """Adjust inventory (can be positive or negative)"""
        try:
            item, created = InventoryItem.objects.get_or_create(
                product=product,
                warehouse=warehouse,
                lot_number=lot_number or '',
                defaults={
                    'quantity': 0,
                    'created_by': self.request.user
                }
            )
            
            item.quantity += quantity
            
            if item.quantity < 0:
                raise Exception("Adjustment would result in negative inventory")
            
            item.save()
            
            # If quantity is zero, optionally delete the item
            if item.quantity == 0:
                item.delete()
            
        except Exception as e:
            raise Exception(f"Error adjusting inventory: {str(e)}")


class CampaignViewSet(viewsets.ModelViewSet):
    """Viewset for agricultural campaigns"""
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'status', 'tenant']
    search_fields = ['name', 'code', 'product__name', 'observations']
    ordering_fields = ['start_date', 'created_at', 'name', 'status']
    ordering = ['-status', '-created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'close_campaign', 'purge_reports']:
            permission_classes = [permissions.IsAuthenticated, IsSupervisorUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

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

        if getattr(user, 'tenant', None):
            return queryset.filter(tenant=user.tenant)

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        tenant = serializer.validated_data.get('tenant')
        if not tenant:
            if getattr(user, 'role', None) == 'superadmin' or user.is_superuser:
                tenant_id = self.request.headers.get('X-Tenant-ID') or self.request.query_params.get('tenant')
                if tenant_id and str(tenant_id).lower() not in ('all', 'undefined', 'null', ''):
                    try:
                        from tenants.models import Tenant
                        tenant = Tenant.objects.filter(id=int(tenant_id)).first()
                    except (ValueError, TypeError):
                        pass
                if not tenant and getattr(user, 'tenant', None):
                    tenant = user.tenant
            else:
                tenant = user.tenant

        serializer.save(created_by=user, tenant=tenant)

    @action(detail=True, methods=['get'])
    def consolidated_report(self, request, pk=None):
        """
        Generate full consolidated report of this campaign:
        Totals, breakdown by producer, breakdown by variety, daily breakdown, and reports list.
        """
        campaign = self.get_object()
        reports = campaign.reports.all().order_by('created_at')

        from django.db.models import Sum, Count, Min, Max
        agg = reports.aggregate(
            total_kilos_netos=Sum('totalPesoNeto'),
            total_kilos_brutos=Sum('totalPesoBruto'),
            total_jabas=Sum('totalJabas'),
            total_cargas=Count('id'),
            first_reception=Min('created_at'),
            last_reception=Max('created_at')
        )

        total_neto = float(agg['total_kilos_netos'] or 0.0)
        total_bruto = float(agg['total_kilos_brutos'] or 0.0)
        total_jabas = int(agg['total_jabas'] or 0)
        total_cargas = int(agg['total_cargas'] or 0)

        producers_map = {}
        varieties_map = {}
        daily_map = {}
        receptions_list = []

        import json
        for r in reports:
            dg = {}
            if r.datosGenerales_json:
                try:
                    dg = json.loads(r.datosGenerales_json)
                except Exception:
                    pass

            prod_name = dg.get('productor') or 'Sin Productor'
            var_name = dg.get('variedad') or 'Sin Variedad'
            date_str = r.created_at.strftime('%Y-%m-%d') if r.created_at else ''
            neto = float(r.totalPesoNeto or 0.0)
            jabas = int(r.totalJabas or 0)

            if prod_name not in producers_map:
                producers_map[prod_name] = {'productor': prod_name, 'kilos': 0.0, 'jabas': 0, 'cargas': 0}
            producers_map[prod_name]['kilos'] = round(producers_map[prod_name]['kilos'] + neto, 2)
            producers_map[prod_name]['jabas'] += jabas
            producers_map[prod_name]['cargas'] += 1

            if var_name not in varieties_map:
                varieties_map[var_name] = {'variedad': var_name, 'kilos': 0.0, 'jabas': 0, 'cargas': 0}
            varieties_map[var_name]['kilos'] = round(varieties_map[var_name]['kilos'] + neto, 2)
            varieties_map[var_name]['jabas'] += jabas
            varieties_map[var_name]['cargas'] += 1

            if date_str not in daily_map:
                daily_map[date_str] = {'date': date_str, 'kilos': 0.0, 'jabas': 0, 'cargas': 0}
            daily_map[date_str]['kilos'] = round(daily_map[date_str]['kilos'] + neto, 2)
            daily_map[date_str]['jabas'] += jabas
            daily_map[date_str]['cargas'] += 1

            receptions_list.append({
                'id': r.id,
                'fecha': r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else '',
                'carga': dg.get('carga') or r.lote,
                'productor': prod_name,
                'clp': dg.get('clp', ''),
                'variedad': var_name,
                'placa': dg.get('placaVehiculo') or dg.get('placa', ''),
                'conductor': dg.get('conductor', ''),
                'peso_bruto': float(r.totalPesoBruto or 0.0),
                'peso_neto': neto,
                'jabas': jabas,
            })

        summary = {
            'campaign_id': campaign.id,
            'campaign_name': campaign.name,
            'campaign_code': campaign.code,
            'product_name': campaign.product.name,
            'tenant_name': campaign.tenant.name,
            'status': campaign.status,
            'start_date': str(campaign.start_date),
            'end_date': str(campaign.end_date) if campaign.end_date else None,
            'total_kilos_netos': round(total_neto, 2),
            'total_kilos_brutos': round(total_bruto, 2),
            'total_jabas': total_jabas,
            'total_cargas': total_cargas,
            'first_reception': agg['first_reception'].isoformat() if agg['first_reception'] else None,
            'last_reception': agg['last_reception'].isoformat() if agg['last_reception'] else None,
            'producers_breakdown': sorted(producers_map.values(), key=lambda x: x['kilos'], reverse=True),
            'varieties_breakdown': sorted(varieties_map.values(), key=lambda x: x['kilos'], reverse=True),
            'daily_breakdown': sorted(daily_map.values(), key=lambda x: x['date']),
            'receptions_sample': receptions_list[:25],
            'receptions_count': len(receptions_list),
        }

        if campaign.status == 'closed' and campaign.closed_summary:
            summary['closed_summary'] = campaign.closed_summary

        return Response(summary)

    @action(detail=True, methods=['post'])
    def close_campaign(self, request, pk=None):
        """
        Close an active campaign:
        1. Generates and freezes the consolidated summary
        2. Sets status='closed', end_date=now.date(), closed_at=now(), closed_by=user
        """
        campaign = self.get_object()
        if campaign.status == 'closed':
            return Response(
                {"error": "La campaña ya se encuentra cerrada."},
                status=status.HTTP_400_BAD_REQUEST
            )

        consolidated_resp = self.consolidated_report(request, pk)
        summary_data = consolidated_resp.data

        from django.utils import timezone
        now = timezone.now()
        campaign.status = Campaign.STATUS_CLOSED
        campaign.closed_summary = summary_data
        campaign.closed_at = now
        campaign.closed_by = request.user
        if not campaign.end_date:
            campaign.end_date = now.date()
        campaign.save()

        serializer = self.get_serializer(campaign)
        return Response({
            "message": f"Campaña '{campaign.name}' cerrada exitosamente con resumen consolidado.",
            "campaign": serializer.data
        })

    @action(detail=True, methods=['post'])
    def purge_reports(self, request, pk=None):
        """
        Purge (hard delete) granular reports from a closed campaign.
        Allowed ONLY if campaign is closed and summary is preserved.
        """
        campaign = self.get_object()
        if campaign.status != 'closed':
            return Response(
                {"error": "Solo se pueden purgar los reportes de una campaña cerrada."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not campaign.closed_summary:
            return Response(
                {"error": "No se puede purgar la campaña porque no cuenta con un resumen consolidado de respaldo."},
                status=status.HTTP_400_BAD_REQUEST
            )

        count = campaign.reports.count()
        if count == 0:
            return Response({
                "message": "La campaña ya no cuenta con reportes individuales asociados.",
                "deleted_count": 0
            })

        campaign.reports.all().delete()

        from django.utils import timezone
        now_str = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        note = f"\n[PURGA REPORTES - {now_str} por {request.user.email}]: Se eliminaron físicamente {count} reportes detallados para optimizar espacio en base de datos. Resumen consolidado preservado intacto."
        campaign.observations = (campaign.observations or '') + note
        campaign.save()

        return Response({
            "message": f"Se purgaron exitosamente {count} reportes individuales de la base de datos. El resumen consolidado de la campaña sigue disponible.",
            "deleted_count": count
        })
