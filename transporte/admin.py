from django.contrib import admin
from .models import TransportCompany, Driver, Vehicle


class DriverInline(admin.TabularInline):
    model = Driver
    extra = 1


class VehicleInline(admin.TabularInline):
    model = Vehicle
    extra = 1


@admin.register(TransportCompany)
class TransportCompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'razon_social', 'ruc', 'tenant', 'phone', 'is_active')
    list_filter = ('tenant', 'is_active')
    search_fields = ('razon_social', 'ruc', 'phone')
    inlines = [DriverInline, VehicleInline]


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'license_number', 'company', 'is_active')
    list_filter = ('is_active', 'company')
    search_fields = ('name', 'license_number', 'company__razon_social')


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('id', 'plate', 'brand_model', 'company', 'is_active')
    list_filter = ('is_active', 'company')
    search_fields = ('plate', 'brand_model', 'company__razon_social')
