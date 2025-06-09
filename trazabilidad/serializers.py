from rest_framework import serializers
from .models import Campo, Cosecha, Lote, LoteEvent, LoteDocument


class CampoSerializer(serializers.ModelSerializer):
    """Serializer for agricultural fields"""
    
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Campo
        fields = (
            'id', 'name', 'location', 'area', 'coordinates',
            'is_organic', 'is_fair_trade', 'is_rainforest',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by', 'created_by_name')
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None
    
    def create(self, validated_data):
        """Create a new campo"""
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)


class CosechaSerializer(serializers.ModelSerializer):
    """Serializer for harvests"""
    
    campo_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    unit_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Cosecha
        fields = (
            'id', 'campo', 'campo_name', 'harvest_date', 'product', 'variety',
            'quantity', 'unit', 'unit_display', 'quality_notes',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by', 'created_by_name', 'campo_name', 'unit_display')
    
    def get_campo_name(self, obj):
        return obj.campo.name
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None
    
    def get_unit_display(self, obj):
        return obj.get_unit_display()
    
    def create(self, validated_data):
        """Create a new cosecha"""
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)


class LoteEventSerializer(serializers.ModelSerializer):
    """Serializer for lot events"""
    
    event_type_display = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = LoteEvent
        fields = (
            'id', 'lote', 'event_type', 'event_type_display',
            'timestamp', 'description', 'created_by', 'created_by_name'
        )
        read_only_fields = ('id', 'timestamp', 'created_by', 'created_by_name', 'event_type_display')
    
    def get_event_type_display(self, obj):
        return obj.get_event_type_display()
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None
    
    def create(self, validated_data):
        """Create a new lote event"""
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)


class LoteDocumentSerializer(serializers.ModelSerializer):
    """Serializer for lot documents"""
    
    document_type_display = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = LoteDocument
        fields = (
            'id', 'lote', 'title', 'file', 'file_type',
            'document_type', 'document_type_display',
            'uploaded_at', 'uploaded_by', 'uploaded_by_name'
        )
        read_only_fields = ('id', 'uploaded_at', 'uploaded_by', 'uploaded_by_name', 'document_type_display')
    
    def get_document_type_display(self, obj):
        return obj.get_document_type_display()
    
    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name()
        return None
    
    def create(self, validated_data):
        """Create a new lote document"""
        user = self.context['request'].user
        validated_data['uploaded_by'] = user
        return super().create(validated_data)


class LoteSerializer(serializers.ModelSerializer):
    """Serializer for production lots"""
    
    events = LoteEventSerializer(many=True, read_only=True)
    documents = LoteDocumentSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    unit_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Lote
        fields = (
            'id', 'lot_number', 'product', 'production_date', 'expiration_date',
            'initial_quantity', 'current_quantity', 'unit', 'unit_display',
            'status', 'status_display', 'cosechas', 'quality_check', 'quality_notes',
            'created_at', 'updated_at', 'created_by', 'created_by_name',
            'events', 'documents'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by', 'created_by_name', 'status_display', 'unit_display')
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None
    
    def get_status_display(self, obj):
        return obj.get_status_display()
    
    def get_unit_display(self, obj):
        return obj.get_unit_display()
    
    def create(self, validated_data):
        """Create a new lote"""
        user = self.context['request'].user
        validated_data['created_by'] = user
        
        # Set current_quantity equal to initial_quantity on creation
        validated_data['current_quantity'] = validated_data.get('initial_quantity')
        
        # Extract cosechas from validated data
        cosechas = validated_data.pop('cosechas', [])
        
        # Create the lote
        lote = super().create(validated_data)
        
        # Add cosechas to the lote
        if cosechas:
            lote.cosechas.set(cosechas)
        
        # Create an initial event
        LoteEvent.objects.create(
            lote=lote,
            event_type=LoteEvent.EVENT_CREATED,
            description=f"Lote {lote.lot_number} created",
            created_by=user
        )
        
        return lote


class LoteListSerializer(serializers.ModelSerializer):
    """Serializer for listing lots (with fewer fields)"""
    
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Lote
        fields = (
            'id', 'lot_number', 'product', 'production_date',
            'current_quantity', 'unit', 'status', 'status_display',
            'created_by_name'
        )
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None
    
    def get_status_display(self, obj):
        return obj.get_status_display()
