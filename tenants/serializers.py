from rest_framework import serializers
from .models import Tenant, Organization


class TenantSummarySerializer(serializers.ModelSerializer):
    """Resumen liviano de Sede para anidar en Organization"""
    users_count = serializers.IntegerField(source='users.count', read_only=True)

    class Meta:
        model = Tenant
        fields = ('id', 'name', 'code', 'ruc', 'address', 'users_count', 'is_active')


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer para Organizaciones (Tenants nivel 2)"""
    sedes_count = serializers.IntegerField(source='sedes.count', read_only=True)
    sedes = TenantSummarySerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = (
            'id', 'name', 'code', 'ruc', 'address', 'is_active',
            'sedes_count', 'sedes', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'sedes_count', 'sedes', 'created_at', 'updated_at')


class TenantSerializer(serializers.ModelSerializer):
    """Serializer para Sedes / Tenants (Nivel 3)"""
    users_count = serializers.IntegerField(source='users.count', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True, default=None)

    class Meta:
        model = Tenant
        fields = (
            'id', 'organization', 'organization_name', 'name', 'code', 'ruc',
            'address', 'allowed_roles', 'users_count', 'is_active',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'organization_name', 'users_count', 'created_at', 'updated_at')
