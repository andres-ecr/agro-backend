from decimal import Decimal
from rest_framework import serializers
from .models import Producer, ProducerCLP


class ProducerCLPSerializer(serializers.ModelSerializer):
    """Serializer para Códigos de Lugar de Producción (CLP) con control de tonelaje"""
    id = serializers.IntegerField(required=False)
    tonelaje_total_tn = serializers.ReadOnlyField()
    tonelaje_saldo_tn = serializers.ReadOnlyField()

    class Meta:
        model = ProducerCLP
        fields = (
            'id', 'producer', 'code', 'lugar_produccion', 'distrito',
            'tonelaje_total', 'tonelaje_saldo', 'tonelaje_total_tn', 'tonelaje_saldo_tn',
            'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('producer', 'tonelaje_total_tn', 'tonelaje_saldo_tn', 'created_at', 'updated_at')


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
        user = getattr(request, 'user', None)
        is_admin = bool(user and (user.is_superuser or getattr(user, 'role', None) in ('admin', 'superadmin')))

        if user and user.is_authenticated:
            validated_data['created_by'] = user
        
        producer = super().create(validated_data)
        
        for item in clp_data:
            clean_item = {k: v for k, v in item.items() if k != 'id'}
            # Inicializar saldo si es nuevo
            total_val = clean_item.get('tonelaje_total') or Decimal('0')
            if 'tonelaje_saldo' not in clean_item or not is_admin:
                clean_item['tonelaje_saldo'] = total_val
            ProducerCLP.objects.create(producer=producer, **clean_item)
            
        # Si tiene campo clp legacy pero no clp_list, sincronizar creando un CLP
        if producer.clp and not clp_data:
            ProducerCLP.objects.create(producer=producer, code=producer.clp)
            
        return producer

    def update(self, instance, validated_data):
        """Actualizar productor y gestionar clp_list anidada con reglas de permisos sobre saldo"""
        clp_data = validated_data.pop('clp_list', None)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        is_admin = bool(user and (user.is_superuser or getattr(user, 'role', None) in ('admin', 'superadmin')))

        instance = super().update(instance, validated_data)

        if clp_data is not None:
            existing_clps = {clp.id: clp for clp in instance.clp_list.all()}
            updated_ids = set()

            for item in clp_data:
                clp_id = item.get('id')
                if clp_id and clp_id in existing_clps:
                    clp_obj = existing_clps[clp_id]
                    old_total = clp_obj.tonelaje_total or Decimal('0')
                    old_saldo = clp_obj.tonelaje_saldo or Decimal('0')

                    new_total = item.get('tonelaje_total', old_total)
                    if new_total is None:
                        new_total = Decimal('0')
                    else:
                        new_total = Decimal(str(new_total))

                    for attr, val in item.items():
                        if attr not in ('id', 'tonelaje_saldo', 'tonelaje_total'):
                            setattr(clp_obj, attr, val)
                    
                    clp_obj.tonelaje_total = new_total

                    if is_admin:
                        # Admins can manually override tonelaje_saldo
                        if 'tonelaje_saldo' in item and item['tonelaje_saldo'] is not None:
                            clp_obj.tonelaje_saldo = Decimal(str(item['tonelaje_saldo']))
                    else:
                        # Non-admins: if total changed (extension), apply delta to remaining balance
                        delta = new_total - old_total
                        if delta != Decimal('0'):
                            clp_obj.tonelaje_saldo = max(Decimal('0'), old_saldo + delta)

                    clp_obj.save()
                    updated_ids.add(clp_id)
                else:
                    clean_item = {k: v for k, v in item.items() if k != 'id'}
                    total_val = clean_item.get('tonelaje_total') or Decimal('0')
                    total_val = Decimal(str(total_val))
                    if 'tonelaje_saldo' not in clean_item or not is_admin:
                        clean_item['tonelaje_saldo'] = total_val
                    new_clp = ProducerCLP.objects.create(producer=instance, **clean_item)
                    updated_ids.add(new_clp.id)

            # Eliminar los CLPs que fueron retirados de la lista
            for clp_id, clp_obj in existing_clps.items():
                if clp_id not in updated_ids:
                    clp_obj.delete()

        return instance


class ProducerListSerializer(serializers.ModelSerializer):
    """Serializer para listar productores incluyendo clp_list y balances de tonelaje"""
    clp_list = ProducerCLPSerializer(many=True, read_only=True)
    tenant_name = serializers.ReadOnlyField(source='tenant.name')
    
    class Meta:
        model = Producer
        fields = ('id', 'tenant', 'tenant_name', 'code', 'name', 'clp', 'address', 'phone', 'email', 'clp_list')
