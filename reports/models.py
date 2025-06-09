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
