from rest_framework import serializers
from .models import Product, ProductVariety, Warehouse, InventoryItem, InventoryMovement


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
    
    product_type_display = serializers.SerializerMethodField()
    unit_display = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    varieties = ProductVarietySerializer(many=True, required=False)
    
    class Meta:
        model = Product
        fields = (
            'id', 'name', 'code', 'description', 'product_type', 'product_type_display',
            'unit', 'unit_display', 'cost', 'price', 'varieties',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by', 'created_by_name', 'product_type_display', 'unit_display')

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
