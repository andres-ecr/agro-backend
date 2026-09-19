from django.db import models


class Organization(models.Model):
    """Modelo para organizaciones / empresas (e.g. AgroExport del Sur, Frutas del Norte)"""
    name = models.CharField(max_length=150, verbose_name="Razón Social / Nombre")
    code = models.CharField(max_length=50, unique=True, verbose_name="Código")
    ruc = models.CharField(max_length=20, blank=True, null=True, verbose_name="RUC")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    logo = models.FileField(upload_to='organizations/logos/', blank=True, null=True, verbose_name="Logo")
    logo_url = models.CharField(max_length=500, blank=True, null=True, verbose_name="URL del Logo")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        ordering = ['name']
        verbose_name = "Organización"
        verbose_name_plural = "Organizaciones"

    def get_logo_url(self):
        if self.logo:
            return self.logo.url
        return self.logo_url

    def __str__(self):
        return f"{self.name} ({self.code})"


class Tenant(models.Model):
    """Modelo para sedes / tenants (e.g. Sede Ica, Sede Casma)"""
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='sedes',
        null=True,
        blank=True,
        verbose_name="Organización / Empresa"
    )
    name = models.CharField(max_length=100, verbose_name="Nombre")
    code = models.CharField(max_length=50, unique=True, verbose_name="Código")
    ruc = models.CharField(max_length=20, blank=True, null=True, verbose_name="RUC")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    logo = models.FileField(upload_to='tenants/logos/', blank=True, null=True, verbose_name="Logo")
    logo_url = models.CharField(max_length=500, blank=True, null=True, verbose_name="URL del Logo")
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

    def get_logo_url(self):
        if self.logo:
            return self.logo.url
        if self.logo_url:
            return self.logo_url
        if self.organization:
            return self.organization.get_logo_url()
        return None

    def __str__(self):
        return f"{self.name} ({self.code})"
