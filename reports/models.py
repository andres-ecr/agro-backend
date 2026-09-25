from django.db import models
from django.conf import settings
import json

class Report(models.Model):
    STATUS_CHOICES = (
        ('completed', 'Completado'),
        ('verified', 'Verificado'),
        ('cancelled', 'Cancelado'),
    )
    
    id = models.CharField(max_length=100, primary_key=True)
    producto = models.CharField(max_length=100)
    lote = models.CharField(max_length=50)
    timestamp = models.BigIntegerField(null=True, blank=True)
    incrementLote = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    
    # Campos JSON para almacenar la estructura completa
    registros_json = models.TextField(null=True, blank=True)
    datosGenerales_json = models.TextField(null=True, blank=True)
    totales_json = models.TextField(null=True, blank=True)
    
    # Campos para totales (para facilitar búsquedas y filtros)
    totalPesoBruto = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    totalPesoNeto = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    totalJabas = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.producto} - {self.lote} - {self.created_at}"

class ReportAttachment(models.Model):
    """Model for report attachments"""
    
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='report_attachments/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Attachment for {self.report.report_id}: {self.file_name}"


class Responsable(models.Model):
    """Modelo para operarios/responsables de recepción para empresas que comparten cuenta en una sola PC"""
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='responsables',
        null=True,
        blank=True,
        verbose_name="Sede / Tenant"
    )
    first_name = models.CharField(max_length=100, verbose_name="Nombre")
    last_name = models.CharField(max_length=100, verbose_name="Apellido")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = "Responsable"
        verbose_name_plural = "Responsables"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.full_name

