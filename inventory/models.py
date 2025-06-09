from django.db import models
from django.conf import settings


class Product(models.Model):
    """Model for products"""
    
    # Product information
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # Product type
    TYPE_RAW = 'raw'
    TYPE_PROCESSED = 'processed'
    TYPE_FINISHED = 'finished'
    TYPE_PACKAGING = 'packaging'
    TYPE_SUPPLY = 'supply'
    
    TYPE_CHOICES = [
        (TYPE_RAW, 'Raw Material'),
        (TYPE_PROCESSED, 'Processed Material'),
        (TYPE_FINISHED, 'Finished Product'),
        (TYPE_PACKAGING, 'Packaging Material'),
        (TYPE_SUPPLY, 'Supply'),
    ]
    
    product_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_FINISHED,
    )
    
    # Units
    UNIT_KG = 'kg'
    UNIT_UNIT = 'unit'
    UNIT_BOX = 'box'
    UNIT_PALLET = 'pallet'
    
    UNIT_CHOICES = [
        (UNIT_KG, 'Kilograms'),
        (UNIT_UNIT, 'Units'),
        (UNIT_BOX, 'Boxes'),
        (UNIT_PALLET, 'Pallets'),
    ]
    
    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default=UNIT_KG,
    )
    
    # Pricing
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products'
    )
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Warehouse(models.Model):
    """Model for warehouses"""
    
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Warehouse type
    TYPE_RAW = 'raw'
    TYPE_PRODUCTION = 'production'
    TYPE_FINISHED = 'finished'
    TYPE_SHIPPING = 'shipping'
    
    TYPE_CHOICES = [
        (TYPE_RAW, 'Raw Materials'),
        (TYPE_PRODUCTION, 'Production'),
        (TYPE_FINISHED, 'Finished Products'),
        (TYPE_SHIPPING, 'Shipping'),
    ]
    
    warehouse_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_FINISHED,
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='warehouses'
    )
    
    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    """Model for inventory items"""
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='inventory_items'
    )
    
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='inventory_items'
    )
    
    # Quantity information
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    min_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_stock = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Lot information
    lot_number = models.CharField(max_length=50, blank=True, null=True)
    expiration_date = models.DateField(null=True, blank=True)
    
    # Status
    STATUS_AVAILABLE = 'available'
    STATUS_RESERVED = 'reserved'
    STATUS_QUARANTINE = 'quarantine'
    
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, 'Available'),
        (STATUS_RESERVED, 'Reserved'),
        (STATUS_QUARANTINE, 'Quarantine'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_AVAILABLE,
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_items'
    )
    
    class Meta:
        unique_together = ('product', 'warehouse', 'lot_number')
    
    def __str__(self):
        return f"{self.product.name} - {self.warehouse.name} - {self.quantity} {self.product.get_unit_display()}"


class InventoryMovement(models.Model):
    """Model for inventory movements"""
    
    # Movement type
    TYPE_IN = 'in'
    TYPE_OUT = 'out'
    TYPE_TRANSFER = 'transfer'
    TYPE_ADJUSTMENT = 'adjustment'
    
    TYPE_CHOICES = [
        (TYPE_IN, 'In'),
        (TYPE_OUT, 'Out'),
        (TYPE_TRANSFER, 'Transfer'),
        (TYPE_ADJUSTMENT, 'Adjustment'),
    ]
    
    movement_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
    )
    
    # Movement information
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='movements'
    )
    
    source_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='source_movements',
        null=True,
        blank=True
    )
    
    destination_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='destination_movements',
        null=True,
        blank=True
    )
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    lot_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Reference information
    reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_movements'
    )
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name} - {self.quantity} - {self.timestamp}"
