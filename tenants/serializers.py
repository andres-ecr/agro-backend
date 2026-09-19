from rest_framework import serializers
from .models import Tenant, Organization


class TenantSummarySerializer(serializers.ModelSerializer):
    """Resumen liviano de Sede para anidar en Organization"""
    users_count = serializers.IntegerField(source='users.count', read_only=True)
    logo_url = serializers.CharField(source='get_logo_url', read_only=True)

    class Meta:
        model = Tenant
        fields = ('id', 'name', 'code', 'ruc', 'address', 'logo_url', 'users_count', 'is_active')


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer para Organizaciones (Tenants nivel 2)"""
    sedes_count = serializers.IntegerField(source='sedes.count', read_only=True)
    sedes = TenantSummarySerializer(many=True, read_only=True)
    effective_logo_url = serializers.CharField(source='get_logo_url', read_only=True)

    class Meta:
        model = Organization
        fields = (
            'id', 'name', 'code', 'ruc', 'address', 'logo', 'logo_url', 'effective_logo_url',
            'is_active', 'sedes_count', 'sedes', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'effective_logo_url', 'sedes_count', 'sedes', 'created_at', 'updated_at')


class TenantSerializer(serializers.ModelSerializer):
    """Serializer para Sedes / Tenants (Nivel 3)"""
    users_count = serializers.IntegerField(source='users.count', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True, default=None)
    effective_logo_url = serializers.CharField(source='get_logo_url', read_only=True)

    class Meta:
        model = Tenant
        fields = (
            'id', 'organization', 'organization_name', 'name', 'code', 'ruc',
            'address', 'logo', 'logo_url', 'effective_logo_url', 'allowed_roles',
            'users_count', 'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'organization_name', 'effective_logo_url', 'users_count', 'created_at', 'updated_at')
