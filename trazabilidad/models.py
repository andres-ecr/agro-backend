from django.db import models
from django.conf import settings


class Campo(models.Model):
    """Model for agricultural fields"""
    
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    area = models.DecimalField(max_digits=10, decimal_places=2, help_text="Area in hectares")
    coordinates = models.JSONField(null=True, blank=True, help_text="GeoJSON coordinates")
    
    # Certifications
    is_organic = models.BooleanField(default=False)
    is_fair_trade = models.BooleanField(default=False)
    is_rainforest = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='campos'
    )
    
    def __str__(self):
        return self.name


class Cosecha(models.Model):
    """Model for harvests"""
    
    campo = models.ForeignKey(
        Campo,
        on_delete=models.CASCADE,
        related_name='cosechas'
    )
    
    # Harvest information
    harvest_date = models.DateField()
    product = models.CharField(max_length=100)
    variety = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Units
    UNIT_KG = 'kg'
    UNIT_TON = 'ton'
    UNIT_BOXES = 'boxes'
    
    UNIT_CHOICES = [
        (UNIT_KG, 'Kilograms'),
        (UNIT_TON, 'Tons'),
        (UNIT_BOXES, 'Boxes'),
    ]
    
    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default=UNIT_KG,
    )
    
    # Quality information
    quality_notes = models.TextField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cosechas'
    )
    
    def __str__(self):
        return f"{self.product} - {self.campo.name} - {self.harvest_date}"


class Lote(models.Model):
    """Model for production lots"""
    
    # Lot identification
    lot_number = models.CharField(max_length=50, unique=True)
    product = models.CharField(max_length=100)
    
    # Dates
    production_date = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)
    
    # Quantity
    initial_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    current_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Units
    UNIT_KG = 'kg'
    UNIT_TON = 'ton'
    UNIT_BOXES = 'boxes'
    
    UNIT_CHOICES = [
        (UNIT_KG, 'Kilograms'),
        (UNIT_TON, 'Tons'),
        (UNIT_BOXES, 'Boxes'),
    ]
    
    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default=UNIT_KG,
    )
    
    # Status
    STATUS_IN_PROCESS = 'in_process'
    STATUS_COMPLETED = 'completed'
    STATUS_SHIPPED = 'shipped'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (STATUS_IN_PROCESS, 'In Process'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_IN_PROCESS,
    )
    
    # Relationships
    cosechas = models.ManyToManyField(
        Cosecha,
        related_name='lotes',
        blank=True
    )
    
    # Quality
    quality_check = models.BooleanField(default=False)
    quality_notes = models.TextField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lotes'
    )
    
    def __str__(self):
        return f"{self.lot_number} - {self.product}"


class LoteEvent(models.Model):
    """Model for lot events (timeline)"""
    
    lote = models.ForeignKey(
        Lote,
        on_delete=models.CASCADE,
        related_name='events'
    )
    
    # Event information
    EVENT_CREATED = 'created'
    EVENT_PROCESSED = 'processed'
    EVENT_QUALITY_CHECK = 'quality_check'
    EVENT_PACKAGED = 'packaged'
    EVENT_SHIPPED = 'shipped'
    EVENT_COMPLETED = 'completed'
    EVENT_CANCELLED = 'cancelled'
    EVENT_NOTE = 'note'
    
    EVENT_CHOICES = [
        (EVENT_CREATED, 'Created'),
        (EVENT_PROCESSED, 'Processed'),
        (EVENT_QUALITY_CHECK, 'Quality Check'),
        (EVENT_PACKAGED, 'Packaged'),
        (EVENT_SHIPPED, 'Shipped'),
        (EVENT_COMPLETED, 'Completed'),
        (EVENT_CANCELLED, 'Cancelled'),
        (EVENT_NOTE, 'Note'),
    ]
    
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_CHOICES,
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lote_events'
    )
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.lote.lot_number} - {self.get_event_type_display()} - {self.timestamp}"


class LoteDocument(models.Model):
    """Model for lot documents"""
    
    lote = models.ForeignKey(
        Lote,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    # Document information
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='lote_documents/')
    file_type = models.CharField(max_length=50)
    
    # Document type
    DOC_CERTIFICATE = 'certificate'
    DOC_QUALITY = 'quality'
    DOC_SHIPPING = 'shipping'
    DOC_OTHER = 'other'
    
    DOC_CHOICES = [
        (DOC_CERTIFICATE, 'Certificate'),
        (DOC_QUALITY, 'Quality Report'),
        (DOC_SHIPPING, 'Shipping Document'),
        (DOC_OTHER, 'Other'),
    ]
    
    document_type = models.CharField(
        max_length=20,
        choices=DOC_CHOICES,
        default=DOC_OTHER,
    )
    
    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lote_documents'
    )
    
    def __str__(self):
        return f"{self.lote.lot_number} - {self.title}"
