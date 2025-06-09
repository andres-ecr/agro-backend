from rest_framework import serializers
from .models import Producer

class ProducerSerializer(serializers.ModelSerializer):
    """Serializer para productores"""
    
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Producer
        fields = (
            'id', 'code', 'name', 'clp', 'address', 'phone', 'email',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by', 'created_by_name')
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None
    
    def create(self, validated_data):
        """Crear un nuevo productor"""
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)

class ProducerListSerializer(serializers.ModelSerializer):
    """Serializer para listar productores (con menos campos)"""
    
    class Meta:
        model = Producer
        fields = ('id', 'code', 'name', 'clp')
