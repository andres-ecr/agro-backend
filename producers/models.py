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
    
    class Meta:
        ordering = ['code']
        verbose_name = "Productor"
        verbose_name_plural = "Productores"
    
    def __str__(self):
        return f"{self.code} - {self.name}"
