from django.contrib import admin
from .models import Tenant, Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'ruc', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'ruc')
    ordering = ('name',)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'organization', 'ruc', 'is_active', 'created_at')
    list_filter = ('is_active', 'organization')
    search_fields = ('name', 'code', 'ruc')
    ordering = ('name',)
