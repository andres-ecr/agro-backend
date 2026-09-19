from django.db import models


class Tenant(models.Model):
    """Modelo para sedes / tenants (e.g. Sede Ica, Sede Casma)"""
    name = models.CharField(max_length=100, verbose_name="Nombre")
    code = models.CharField(max_length=50, unique=True, verbose_name="Código")
    ruc = models.CharField(max_length=20, blank=True, null=True, verbose_name="RUC")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    allowed_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="List of allowed roles for this tenant, e.g. ['admin', 'operator']"
    )
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        ordering = ['name']
        verbose_name = "Sede / Tenant"
        verbose_name_plural = "Sedes / Tenants"

    def __str__(self):
        return f"{self.name} ({self.code})"
