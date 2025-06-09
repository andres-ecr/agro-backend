from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Warehouse, InventoryItem, InventoryMovement
from .serializers import ProductSerializer, WarehouseSerializer, InventoryItemSerializer, InventoryMovementSerializer
from users.permissions import IsOwnerOrAdmin, IsSupervisorUser


class ProductViewSet(viewsets.ModelViewSet):
    """Viewset for products"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product_type', 'unit']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['name']
    
    def get_permissions(self):
        """Set custom permissions for each action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsSupervisorUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]


class WarehouseViewSet(viewsets.ModelViewSet):
    """Viewset for warehouses"""
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['warehouse_type']
    search_fields = ['name', 'location', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_permissions(self):
        """Set custom permissions for each action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsSupervisorUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]


class InventoryItemViewSet(viewsets.ModelViewSet):
    """Viewset for inventory items"""
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'warehouse', 'status', 'lot_number']
    search_fields = ['product__name', 'product__code', 'lot_number']
    ordering_fields = ['product__name', 'quantity', 'expiration_date']
    ordering = ['product__name']
    
    def get_permissions(self):
        """Set custom permissions for each action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsSupervisorUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['POST'])
    def update_status(self, request, pk=None):
        """Update the status of an inventory item"""
        item = self.get_object()
        
        # Check if user has permission (supervisor or admin)
        self.check_object_permissions(request, item)
        
        # Get new status from request
        new_status = request.data.get('status')
        if not new_status or new_status not in dict(InventoryItem.STATUS_CHOICES):
            return Response(
                {"detail": "Invalid status."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update item status
        item.status = new_status
        item.save()
        
        serializer = self.get_serializer(item)
        return Response(serializer.data)


class InventoryMovementViewSet(viewsets.ModelViewSet):
    """Viewset for inventory movements"""
    queryset = InventoryMovement.objects.all()
    serializer_class = InventoryMovementSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['movement_type', 'product', 'source_warehouse', 'destination_warehouse', 'lot_number']
    search_fields = ['product__name', 'product__code', 'reference', 'notes']
    ordering_fields = ['timestamp', 'product__name']
    ordering = ['-timestamp']
    
    def get_permissions(self):
        """Set custom permissions for each action"""
        if self.action in ['create']:
            permission_classes = [permissions.IsAuthenticated, IsSupervisorUser]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def create(self, validated_data):
        """Create a new inventory movement and update inventory"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get validated data
        movement_type = serializer.validated_data.get('movement_type')
        product = serializer.validated_data.get('product')
        source_warehouse = serializer.validated_data.get('source_warehouse')
        destination_warehouse = serializer.validated_data.get('destination_warehouse')
        quantity = serializer.validated_data.get('quantity')
        lot_number = serializer.validated_data.get('lot_number')
        
        # Validate movement data
        if movement_type == InventoryMovement.TYPE_IN and not destination_warehouse:
            return Response(
                {"detail": "Destination warehouse is required for IN movements."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if movement_type == InventoryMovement.TYPE_OUT and not source_warehouse:
            return Response(
                {"detail": "Source warehouse is required for OUT movements."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if movement_type == InventoryMovement.TYPE_TRANSFER and (not source_warehouse or not destination_warehouse):
            return Response(
                {"detail": "Source and destination warehouses are required for TRANSFER movements."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the movement
        movement = serializer.save(created_by=self.request.user)
        
        # Update inventory based on movement type
        try:
            if movement_type == InventoryMovement.TYPE_IN:
                # Add to destination warehouse
                self._add_to_inventory(product, destination_warehouse, quantity, lot_number)
            
            elif movement_type == InventoryMovement.TYPE_OUT:
                # Remove from source warehouse
                self._remove_from_inventory(product, source_warehouse, quantity, lot_number)
            
            elif movement_type == InventoryMovement.TYPE_TRANSFER:
                # Remove from source and add to destination
                self._remove_from_inventory(product, source_warehouse, quantity, lot_number)
                self._add_to_inventory(product, destination_warehouse, quantity, lot_number)
            
            elif movement_type == InventoryMovement.TYPE_ADJUSTMENT:
                # Handle adjustment (could be positive or negative)
                if source_warehouse:
                    self._adjust_inventory(product, source_warehouse, -quantity, lot_number)
                if destination_warehouse:
                    self._adjust_inventory(product, destination_warehouse, quantity, lot_number)
        
        except Exception as e:
            # If inventory update fails, delete the movement and return error
            movement.delete()
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def _add_to_inventory(self, product, warehouse, quantity, lot_number):
        """Add quantity to inventory"""
        try:
            item, created = InventoryItem.objects.get_or_create(
                product=product,
                warehouse=warehouse,
                lot_number=lot_number or '',
                defaults={
                    'quantity': 0,
                    'created_by': self.request.user
                }
            )
            
            item.quantity += quantity
            item.save()
            
        except Exception as e:
            raise Exception(f"Error adding to inventory: {str(e)}")
    
    def _remove_from_inventory(self, product, warehouse, quantity, lot_number):
        """Remove quantity from inventory"""
        try:
            # Get the inventory item
            item = InventoryItem.objects.filter(
                product=product,
                warehouse=warehouse,
                lot_number=lot_number or ''
            ).first()
            
            if not item:
                raise Exception("Inventory item not found")
            
            if item.quantity < quantity:
                raise Exception("Insufficient quantity in inventory")
            
            item.quantity -= quantity
            item.save()
            
            # If quantity is zero, optionally delete the item
            if item.quantity == 0:
                item.delete()
            
        except Exception as e:
            raise Exception(f"Error removing from inventory: {str(e)}")
    
    def _adjust_inventory(self, product, warehouse, quantity, lot_number):
        """Adjust inventory (can be positive or negative)"""
        try:
            item, created = InventoryItem.objects.get_or_create(
                product=product,
                warehouse=warehouse,
                lot_number=lot_number or '',
                defaults={
                    'quantity': 0,
                    'created_by': self.request.user
                }
            )
            
            item.quantity += quantity
            
            if item.quantity < 0:
                raise Exception("Adjustment would result in negative inventory")
            
            item.save()
            
            # If quantity is zero, optionally delete the item
            if item.quantity == 0:
                item.delete()
            
        except Exception as e:
            raise Exception(f"Error adjusting inventory: {str(e)}")
