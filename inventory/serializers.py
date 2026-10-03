from rest_framework import serializers
from django.db.models import Sum
from tenants.models import Tenant
from .models import Product, ProductVariety, Warehouse, InventoryItem, InventoryMovement, Campaign


class ProductVarietySerializer(serializers.ModelSerializer):
    """Serializer for product varieties"""
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ProductVariety
        fields = ('id', 'name', 'code', 'is_active')

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = {'name': data}
        return super().to_internal_value(data)


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for products"""
    
    tenant_name = serializers.ReadOnlyField(source='tenant.name')
    product_type_display = serializers.SerializerMethodField()
    unit_display = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    varieties = ProductVarietySerializer(many=True, required=False)
    active_campaign = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = (
            'id', 'tenant', 'tenant_name', 'name', 'code', 'description', 'product_type', 'product_type_display',
            'unit', 'unit_display', 'cost', 'price', 'varieties', 'active_campaign',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by', 'created_by_name', 'product_type_display', 'unit_display', 'tenant_name', 'active_campaign')

    def get_active_campaign(self, obj):
        active = obj.campaigns.filter(status='active').first()
        if active:
            return {
                'id': active.id,
                'name': active.name,
                'code': active.code,
                'status': active.status,
                'start_date': str(active.start_date),
            }
        return None

    def to_internal_value(self, data):
        if 'varieties' in data and isinstance(data['varieties'], list):
            normalized = []
            for item in data['varieties']:
                if isinstance(item, str):
                    normalized.append({'name': item})
                else:
                    normalized.append(item)
            if hasattr(data, '_mutable') and not data._mutable:
                data = data.copy()
            elif isinstance(data, dict):
                data = dict(data)
            data['varieties'] = normalized
        return super().to_internal_value(data)
    
    def get_product_type_display(self, obj):
        return obj.get_product_type_display()
    
    def get_unit_display(self, obj):
        return obj.get_unit_display()
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None
    
    def create(self, validated_data):
        """Create a new product with optional varieties"""
        varieties_data = self.initial_data.get('varieties', None)
        if varieties_data is None:
            varieties_data = validated_data.pop('varieties', [])
        elif 'varieties' in validated_data:
            validated_data.pop('varieties')

        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            if 'tenant' not in validated_data:
                if getattr(request.user, 'role', None) != 'superadmin' and not request.user.is_superuser:
                    validated_data['tenant'] = getattr(request.user, 'tenant', None)
                else:
                    tenant_id = request.headers.get('X-Tenant-ID') if hasattr(request, 'headers') else None
                    if tenant_id and str(tenant_id).lower() not in ('all', 'undefined', 'null', ''):
                        try:
                            from tenants.models import Tenant
                            validated_data['tenant'] = Tenant.objects.filter(id=int(tenant_id)).first()
                        except (ValueError, TypeError):
                            pass
                    if 'tenant' not in validated_data and getattr(request.user, 'tenant', None):
                        validated_data['tenant'] = request.user.tenant
        
        product = super().create(validated_data)

        if varieties_data:
            for item in varieties_data:
                if isinstance(item, str):
                    name = item.strip()
                    code = None
                    is_active = True
                elif isinstance(item, dict):
                    name = item.get('name', '').strip()
                    code = item.get('code')
                    is_active = item.get('is_active', True)
                else:
                    continue
                
                if name:
                    ProductVariety.objects.get_or_create(
                        product=product,
                        name=name,
                        defaults={'code': code, 'is_active': is_active}
                    )
        
        return product

    def update(self, instance, validated_data):
        """Update product and sync varieties if provided"""
        varieties_data = self.initial_data.get('varieties', None)
        if varieties_data is None and 'varieties' in validated_data:
            varieties_data = validated_data.pop('varieties')
        elif 'varieties' in validated_data:
            validated_data.pop('varieties')

        instance = super().update(instance, validated_data)

        if varieties_data is not None:
            existing_varieties = list(instance.varieties.all())
            existing_by_id = {v.id: v for v in existing_varieties}
            existing_by_name = {v.name.lower(): v for v in existing_varieties}
            kept_ids = set()

            for item in varieties_data:
                if isinstance(item, str):
                    name = item.strip()
                    code = None
                    is_active = True
                    var_id = None
                elif isinstance(item, dict):
                    name = item.get('name', '').strip()
                    code = item.get('code')
                    is_active = item.get('is_active', True)
                    var_id = item.get('id')
                else:
                    continue

                if not name:
                    continue

                if var_id and var_id in existing_by_id:
                    var_obj = existing_by_id[var_id]
                    var_obj.name = name
                    if code is not None:
                        var_obj.code = code
                    var_obj.is_active = is_active
                    var_obj.save()
                    kept_ids.add(var_obj.id)
                elif name.lower() in existing_by_name:
                    var_obj = existing_by_name[name.lower()]
                    var_obj.name = name
                    if code is not None:
                        var_obj.code = code
                    var_obj.is_active = is_active
                    var_obj.save()
                    kept_ids.add(var_obj.id)
                else:
                    new_var = ProductVariety.objects.create(
                        product=instance,
                        name=name,
                        code=code,
                        is_active=is_active
                    )
                    kept_ids.add(new_var.id)

            instance.varieties.exclude(id__in=kept_ids).delete()

        return instance


class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for agricultural campaigns"""
    tenant = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), required=False)
    product_name = serializers.ReadOnlyField(source='product.name')
    tenant_name = serializers.ReadOnlyField(source='tenant.name')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    closed_by_name = serializers.SerializerMethodField()
    
    total_kilos = serializers.SerializerMethodField()
    total_jabas = serializers.SerializerMethodField()
    total_cargas = serializers.SerializerMethodField()
    reports_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = (
            'id', 'tenant', 'tenant_name', 'product', 'product_name',
            'name', 'code', 'status', 'status_display',
            'start_date', 'end_date', 'closed_at', 'closed_by', 'closed_by_name',
            'closed_summary', 'observations',
            'total_kilos', 'total_jabas', 'total_cargas', 'reports_count',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        )
        read_only_fields = (
            'id', 'status_display', 'closed_at', 'closed_by', 'closed_by_name',
            'closed_summary', 'tenant_name', 'product_name',
            'total_kilos', 'total_jabas', 'total_cargas', 'reports_count',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        )

    def to_internal_value(self, data):
        if hasattr(data, '_mutable') and not data._mutable:
            data = data.copy()
        elif isinstance(data, dict):
            data = dict(data)

        if not data.get('tenant'):
            prod_val = data.get('product')
            if prod_val:
                try:
                    prod = Product.objects.filter(id=prod_val).first() if isinstance(prod_val, (int, str)) and str(prod_val).isdigit() else None
                    if prod and prod.tenant_id:
                        data['tenant'] = prod.tenant_id
                except Exception:
                    pass

            if not data.get('tenant'):
                request = self.context.get('request')
                if request:
                    user = getattr(request, 'user', None)
                    if user:
                        if getattr(user, 'tenant_id', None):
                            data['tenant'] = user.tenant_id
                        elif getattr(user, 'role', None) == 'superadmin' or getattr(user, 'is_superuser', False):
                            tenant_id = request.headers.get('X-Tenant-ID') or request.query_params.get('tenant')
                            if tenant_id and str(tenant_id).lower() not in ('all', 'undefined', 'null', ''):
                                data['tenant'] = tenant_id

        return super().to_internal_value(data)

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None

    def get_closed_by_name(self, obj):
        if obj.closed_by:
            return obj.closed_by.get_full_name() or obj.closed_by.email
        return None

    def get_total_kilos(self, obj):
        if obj.status == 'closed' and obj.closed_summary:
            return obj.closed_summary.get('total_kilos_netos', 0.0)
        val = obj.reports.aggregate(total=Sum('totalPesoNeto'))['total']
        return float(val or 0.0)

    def get_total_jabas(self, obj):
        if obj.status == 'closed' and obj.closed_summary:
            return obj.closed_summary.get('total_jabas', 0)
        val = obj.reports.aggregate(total=Sum('totalJabas'))['total']
        return int(val or 0)

    def get_total_cargas(self, obj):
        if obj.status == 'closed' and obj.closed_summary:
            return obj.closed_summary.get('total_cargas', 0)
        return obj.reports.count()

    def get_reports_count(self, obj):
        return obj.reports.count()

    def validate(self, attrs):
        product = attrs.get('product') or (self.instance.product if self.instance else None)
        tenant = attrs.get('tenant') or (self.instance.tenant if self.instance else None)
        status_val = attrs.get('status', 'active')

        request = self.context.get('request')
        if not tenant:
            if product and getattr(product, 'tenant', None):
                tenant = product.tenant
                attrs['tenant'] = tenant
            elif request:
                user = request.user
                if getattr(user, 'tenant', None):
                    tenant = user.tenant
                    attrs['tenant'] = tenant
                elif getattr(user, 'role', None) == 'superadmin' or user.is_superuser:
                    tenant_id = request.headers.get('X-Tenant-ID') or request.query_params.get('tenant')
                    if tenant_id and str(tenant_id).lower() not in ('all', 'undefined', 'null', ''):
                        try:
                            tenant = Tenant.objects.filter(id=int(tenant_id)).first()
                            if tenant:
                                attrs['tenant'] = tenant
                        except (ValueError, TypeError):
                            pass
                    if not tenant and getattr(user, 'tenant', None):
                        tenant = user.tenant
                        attrs['tenant'] = tenant

        if not tenant:
            raise serializers.ValidationError({
                'tenant': 'Debe especificar o tener asignada una sede para la campaña.'
            })

        name_val = attrs.get('name') or (self.instance.name if self.instance else None)
        if name_val and tenant:
            name_qs = Campaign.objects.filter(tenant=tenant, name__iexact=str(name_val).strip())
            if self.instance:
                name_qs = name_qs.exclude(id=self.instance.id)
            if name_qs.exists():
                existing = name_qs.first()
                raise serializers.ValidationError({
                    'name': f"Ya existe una campaña registrada con el nombre '{name_val}' en esta sede (estado: {existing.get_status_display()}). Ingrese un nombre diferente o agregue el año/temporada (ej: '{name_val} 2026')."
                })

        if status_val == 'active' and product and tenant:
            qs = Campaign.objects.filter(tenant=tenant, product=product, status='active')
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError(
                    f"Ya existe una campaña activa para el producto '{product.name}' en esta sede ({qs.first().name}). Debe cerrar la campaña actual antes de iniciar una nueva."
                )
        return attrs


class WarehouseSerializer(serializers.ModelSerializer):
    """Serializer for warehouses"""
    
    warehouse_type_display = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Warehouse
        fields = (
            'id', 'name', 'location', 'description', 'warehouse_type', 'warehouse_type_display',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by', 'created_by_name', 'warehouse_type_display')
    
    def get_warehouse_type_display(self, obj):
        return obj.get_warehouse_type_display()
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None
    
    def create(self, validated_data):
        """Create a new warehouse"""
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)


class InventoryItemSerializer(serializers.ModelSerializer):
    """Serializer for inventory items"""
    
    product_name = serializers.SerializerMethodField()
    warehouse_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    unit_display = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryItem
        fields = (
            'id', 'product', 'product_name', 'warehouse', 'warehouse_name',
            'quantity', 'min_stock', 'max_stock', 'lot_number', 'expiration_date',
            'status', 'status_display', 'unit_display',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by', 'created_by_name', 'product_name', 'warehouse_name', 'status_display', 'unit_display')
    
    def get_product_name(self, obj):
        return obj.product.name
    
    def get_warehouse_name(self, obj):
        return obj.warehouse.name
    
    def get_status_display(self, obj):
        return obj.get_status_display()
    
    def get_unit_display(self, obj):
        return obj.product.get_unit_display()
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None
    
    def create(self, validated_data):
        """Create a new inventory item"""
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)


class InventoryMovementSerializer(serializers.ModelSerializer):
    """Serializer for inventory movements"""
    
    product_name = serializers.SerializerMethodField()
    source_warehouse_name = serializers.SerializerMethodField()
    destination_warehouse_name = serializers.SerializerMethodField()
    movement_type_display = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryMovement
        fields = (
            'id', 'movement_type', 'movement_type_display', 'product', 'product_name',
            'source_warehouse', 'source_warehouse_name', 'destination_warehouse', 'destination_warehouse_name',
            'quantity', 'lot_number', 'reference', 'notes',
            'timestamp', 'created_by', 'created_by_name'
        )
        read_only_fields = ('id', 'timestamp', 'created_by', 'created_by_name', 'product_name', 'source_warehouse_name', 'destination_warehouse_name', 'movement_type_display')
    
    def get_product_name(self, obj):
        return obj.product.name
    
    def get_source_warehouse_name(self, obj):
        if obj.source_warehouse:
            return obj.source_warehouse.name
        return None
    
    def get_destination_warehouse_name(self, obj):
        if obj.destination_warehouse:
            return obj.destination_warehouse.name
        return None
    
    def get_movement_type_display(self, obj):
        return obj.get_movement_type_display()
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None
    
    def create(self, validated_data):
        """Create a new inventory movement"""
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)
