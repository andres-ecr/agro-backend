from rest_framework import serializers
from .models import Producer, ProducerCLP


class ProducerCLPSerializer(serializers.ModelSerializer):
    """Serializer para Códigos de Lugar de Producción (CLP)"""
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ProducerCLP
        fields = ('id', 'producer', 'code', 'lugar_produccion', 'distrito', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('producer', 'created_at', 'updated_at')


class ProducerSerializer(serializers.ModelSerializer):
    """Serializer para productores con lista de CLPs anidada"""
    
    created_by_name = serializers.SerializerMethodField()
    clp_list = ProducerCLPSerializer(many=True, required=False)
    tenant_name = serializers.ReadOnlyField(source='tenant.name')
    
    class Meta:
        model = Producer
        fields = (
            'id', 'tenant', 'tenant_name', 'code', 'name', 'clp', 'address', 'phone', 'email',
            'clp_list',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by', 'created_by_name')
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None
    
    def create(self, validated_data):
        """Crear un nuevo productor y sus CLPs asociados"""
        clp_data = validated_data.pop('clp_list', [])
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        
        producer = super().create(validated_data)
        
        for item in clp_data:
            clean_item = {k: v for k, v in item.items() if k != 'id'}
            ProducerCLP.objects.create(producer=producer, **clean_item)
            
        # Si tiene campo clp legacy pero no clp_list, sincronizar creando un CLP
        if producer.clp and not clp_data:
            ProducerCLP.objects.create(producer=producer, code=producer.clp)
            
        return producer

    def update(self, instance, validated_data):
        """Actualizar productor y gestionar clp_list anidada"""
        clp_data = validated_data.pop('clp_list', None)
        instance = super().update(instance, validated_data)

        if clp_data is not None:
            existing_clps = {clp.id: clp for clp in instance.clp_list.all()}
            updated_ids = set()

            for item in clp_data:
                clp_id = item.get('id')
                if clp_id and clp_id in existing_clps:
                    clp_obj = existing_clps[clp_id]
                    for attr, val in item.items():
                        if attr != 'id':
                            setattr(clp_obj, attr, val)
                    clp_obj.save()
                    updated_ids.add(clp_id)
                else:
                    clean_item = {k: v for k, v in item.items() if k != 'id'}
                    new_clp = ProducerCLP.objects.create(producer=instance, **clean_item)
                    updated_ids.add(new_clp.id)

            # Eliminar los CLPs que fueron retirados de la lista
            for clp_id, clp_obj in existing_clps.items():
                if clp_id not in updated_ids:
                    clp_obj.delete()

        return instance


class ProducerListSerializer(serializers.ModelSerializer):
    """Serializer para listar productores (con menos campos) incluyendo clp_list"""
    clp_list = ProducerCLPSerializer(many=True, read_only=True)
    tenant_name = serializers.ReadOnlyField(source='tenant.name')
    
    class Meta:
        model = Producer
        fields = ('id', 'tenant', 'tenant_name', 'code', 'name', 'clp', 'address', 'phone', 'email', 'clp_list')

