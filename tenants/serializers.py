from rest_framework import serializers
from .models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(source='users.count', read_only=True)

    class Meta:
        model = Tenant
        fields = (
            'id', 'name', 'code', 'ruc', 'address', 'allowed_roles',
            'users_count', 'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'users_count', 'created_at', 'updated_at')
