from django.db import models


class TransportCompany(models.Model):
    """Modelo para empresas de transporte (transportistas)"""
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='transport_companies',
        null=True,
        blank=True,
        verbose_name="Sede / Tenant"
    )
    ruc = models.CharField(max_length=20, db_index=True, verbose_name="RUC")
    razon_social = models.CharField(max_length=200, verbose_name="Razón Social")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Teléfono")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        ordering = ['razon_social']
        verbose_name = "Empresa de Transporte"
        verbose_name_plural = "Empresas de Transporte"

    def __str__(self):
        return f"{self.razon_social} ({self.ruc})"


class Driver(models.Model):
    """Modelo para choferes de empresas de transporte"""
    company = models.ForeignKey(
        TransportCompany,
        on_delete=models.CASCADE,
        related_name='drivers',
        verbose_name="Empresa de Transporte"
    )
    name = models.CharField(max_length=150, verbose_name="Nombre del Chofer")
    license_number = models.CharField(max_length=50, verbose_name="Número de Licencia / Brevete")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="Fecha de actualización")

    class Meta:
        ordering = ['name']
        verbose_name = "Chofer"
        verbose_name_plural = "Choferes"

    def __str__(self):
        return f"{self.name} ({self.license_number})"


class Vehicle(models.Model):
    """Modelo para vehículos / camiones de empresas de transporte"""
    company = models.ForeignKey(
        TransportCompany,
        on_delete=models.CASCADE,
        related_name='vehicles',
        verbose_name="Empresa de Transporte"
    )
    plate = models.CharField(max_length=20, verbose_name="Placa")
    brand_model = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marca / Modelo")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="Fecha de actualización")

    class Meta:
        ordering = ['plate']
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"

    def __str__(self):
        return f"{self.plate} - {self.brand_model or 'Sin modelo'}"
