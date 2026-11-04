from django.db import models
from django.conf import settings

class Producer(models.Model):
    """Modelo para productores agrícolas"""
    
    code = models.CharField(max_length=50, unique=True, verbose_name="Código")
    name = models.CharField(max_length=200, verbose_name="Nombre")
    clp = models.CharField(max_length=100, blank=True, null=True, verbose_name="CLP")
    
    # Campos adicionales que podrían ser útiles
    address = models.TextField(blank=True, null=True, verbose_name="Dirección")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='producers',
        verbose_name="Creado por"
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='producers',
        null=True,
        blank=True,
        verbose_name='Sede'
    )
    
    class Meta:
        ordering = ['code']
        verbose_name = "Productor"
        verbose_name_plural = "Productores"
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class ProducerCLP(models.Model):
    """Modelo para múltiples códigos de Lugar de Producción (CLP) de un productor"""
    producer = models.ForeignKey(
        Producer,
        on_delete=models.CASCADE,
        related_name='clp_list',
        verbose_name="Productor"
    )
    code = models.CharField(max_length=100, verbose_name="Código CLP")
    lugar_produccion = models.CharField(max_length=200, blank=True, null=True, verbose_name="Lugar de Producción")
    distrito = models.CharField(max_length=100, blank=True, null=True, verbose_name="Distrito")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    
    # Control de Tonelaje / Cupo SENASA por Lugar de Producción (en KG)
    tonelaje_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Tonelaje Total Autorizado (KG)"
    )
    tonelaje_saldo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Saldo Restante CLP (KG)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        ordering = ['code']
        verbose_name = "CLP de Productor"
        verbose_name_plural = "CLPs de Productores"

    @property
    def tonelaje_total_tn(self):
        return round(float(self.tonelaje_total or 0) / 1000.0, 3)

    @property
    def tonelaje_saldo_tn(self):
        return round(float(self.tonelaje_saldo or 0) / 1000.0, 3)

    def __str__(self):
        return f"{self.producer.name} - CLP: {self.code}"
