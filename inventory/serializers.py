from rest_framework import serializers
from .models import Product, Warehouse, InventoryItem, InventoryMovement


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for products"""
    
    product_type_display = serializers.SerializerMethodField()
    unit_display = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = (
            'id', 'name', 'code', 'description', 'product_type', 'product_type_display',
            'unit', 'unit_display', 'cost', 'price',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by', 'created_by_name', 'product_type_display', 'unit_display')
    
    def get_product_type_display(self, obj):
        return obj.get_product_type_display()
    
    def get_unit_display(self, obj):
        return obj.get_unit_display()
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None
    
    def create(self, validated_data):
        """Create a new product"""
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)


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
