from rest_framework import serializers
from .models import TransportCompany, Driver, Vehicle


class DriverSerializer(serializers.ModelSerializer):
    company_name = serializers.ReadOnlyField(source='company.razon_social')

    class Meta:
        model = Driver
        fields = ('id', 'company', 'company_name', 'name', 'license_number', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class DriverNestedSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Driver
        fields = ('id', 'name', 'license_number', 'is_active')


class VehicleSerializer(serializers.ModelSerializer):
    company_name = serializers.ReadOnlyField(source='company.razon_social')

    class Meta:
        model = Vehicle
        fields = ('id', 'company', 'company_name', 'plate', 'brand_model', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class VehicleNestedSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Vehicle
        fields = ('id', 'plate', 'brand_model', 'is_active')


class TransportCompanySerializer(serializers.ModelSerializer):
    """Serializer para TransportCompany con drivers y vehicles anidados"""
    drivers = DriverNestedSerializer(many=True, required=False)
    vehicles = VehicleNestedSerializer(many=True, required=False)
    tenant_name = serializers.ReadOnlyField(source='tenant.name')

    class Meta:
        model = TransportCompany
        fields = (
            'id', 'tenant', 'tenant_name', 'ruc', 'razon_social',
            'address', 'phone', 'is_active', 'created_at', 'updated_at',
            'drivers', 'vehicles'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def create(self, validated_data):
        drivers_data = validated_data.pop('drivers', [])
        vehicles_data = validated_data.pop('vehicles', [])
        company = TransportCompany.objects.create(**validated_data)
        
        for d in drivers_data:
            d_clean = {k: v for k, v in d.items() if k != 'id'}
            Driver.objects.create(company=company, **d_clean)
            
        for v in vehicles_data:
            v_clean = {k: v for k, v in v.items() if k != 'id'}
            Vehicle.objects.create(company=company, **v_clean)
            
        return company

    def update(self, instance, validated_data):
        drivers_data = validated_data.pop('drivers', None)
        vehicles_data = validated_data.pop('vehicles', None)
        
        instance = super().update(instance, validated_data)
        
        if drivers_data is not None:
            existing_drivers = {d.id: d for d in instance.drivers.all()}
            updated_ids = set()
            for d in drivers_data:
                d_id = d.get('id')
                if d_id and d_id in existing_drivers:
                    driver_obj = existing_drivers[d_id]
                    for attr, val in d.items():
                        if attr != 'id':
                            setattr(driver_obj, attr, val)
                    driver_obj.save()
                    updated_ids.add(d_id)
                else:
                    d_clean = {k: v for k, v in d.items() if k != 'id'}
                    new_d = Driver.objects.create(company=instance, **d_clean)
                    updated_ids.add(new_d.id)
            for d_id, d_obj in existing_drivers.items():
                if d_id not in updated_ids:
                    d_obj.delete()

        if vehicles_data is not None:
            existing_vehicles = {v.id: v for v in instance.vehicles.all()}
            updated_ids = set()
            for v in vehicles_data:
                v_id = v.get('id')
                if v_id and v_id in existing_vehicles:
                    veh_obj = existing_vehicles[v_id]
                    for attr, val in v.items():
                        if attr != 'id':
                            setattr(veh_obj, attr, val)
                    veh_obj.save()
                    updated_ids.add(v_id)
                else:
                    v_clean = {k: v for k, v in v.items() if k != 'id'}
                    new_v = Vehicle.objects.create(company=instance, **v_clean)
                    updated_ids.add(new_v.id)
            for v_id, v_obj in existing_vehicles.items():
                if v_id not in updated_ids:
                    v_obj.delete()

        return instance
