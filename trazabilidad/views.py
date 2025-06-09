from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Campo, Cosecha, Lote, LoteEvent, LoteDocument
from .serializers import (
    CampoSerializer, CosechaSerializer, LoteSerializer, LoteListSerializer,
    LoteEventSerializer, LoteDocumentSerializer
)
from users.permissions import IsOwnerOrAdmin, IsSupervisorUser


class CampoViewSet(viewsets.ModelViewSet):
    """Viewset for agricultural fields"""
    queryset = Campo.objects.all()
    serializer_class = CampoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_organic', 'is_fair_trade', 'is_rainforest']
    search_fields = ['name', 'location']
    ordering_fields = ['name', 'area', 'created_at']
    ordering = ['name']
    
    def get_permissions(self):
        """Set custom permissions for each action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsSupervisorUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]


class CosechaViewSet(viewsets.ModelViewSet):
    """Viewset for harvests"""
    queryset = Cosecha.objects.all()
    serializer_class = CosechaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['campo', 'product', 'harvest_date']
    search_fields = ['product', 'variety', 'quality_notes']
    ordering_fields = ['harvest_date', 'product', 'quantity']
    ordering = ['-harvest_date']
    
    def get_permissions(self):
        """Set custom permissions for each action"""
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]


class LoteViewSet(viewsets.ModelViewSet):
    """Viewset for production lots"""
    queryset = Lote.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'status', 'quality_check']
    search_fields = ['lot_number', 'product', 'quality_notes']
    ordering_fields = ['production_date', 'product', 'current_quantity', 'status']
    ordering = ['-production_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LoteListSerializer
        return LoteSerializer
    
    def get_permissions(self):
        """Set custom permissions for each action"""
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
        elif self.action in ['quality_check']:
            permission_classes = [permissions.IsAuthenticated, IsSupervisorUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['POST'])
    def add_event(self, request, pk=None):
        """Add an event to a lot"""
        lote = self.get_object()
        
        # Create serializer with request data
        serializer = LoteEventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(lote=lote, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['POST'])
    def quality_check(self, request, pk=None):
        """Perform quality check on a lot (only supervisors and admins)"""
        lote = self.get_object()
        
        # Update lot with quality check
        lote.quality_check = True
        lote.quality_notes = request.data.get('quality_notes', '')
        lote.save()
        
        # Create quality check event
        LoteEvent.objects.create(
            lote=lote,
            event_type=LoteEvent.EVENT_QUALITY_CHECK,
            description=f"Quality check performed: {lote.quality_notes}",
            created_by=request.user
        )
        
        serializer = self.get_serializer(lote)
        return Response(serializer.data)
    
    @action(detail=True, methods=['POST'])
    def update_status(self, request, pk=None):
        """Update the status of a lot"""
        lote = self.get_object()
        
        # Check if user has permission (owner or admin)
        self.check_object_permissions(request, lote)
        
        # Get new status from request
        new_status = request.data.get('status')
        if not new_status or new_status not in dict(Lote.STATUS_CHOICES):
            return Response(
                {"detail": "Invalid status."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update lot status
        lote.status = new_status
        lote.save()
        
        # Create status update event
        event_type_map = {
            Lote.STATUS_COMPLETED: LoteEvent.EVENT_COMPLETED,
            Lote.STATUS_SHIPPED: LoteEvent.EVENT_SHIPPED,
            Lote.STATUS_CANCELLED: LoteEvent.EVENT_CANCELLED,
        }
        
        event_type = event_type_map.get(new_status, LoteEvent.EVENT_NOTE)
        
        LoteEvent.objects.create(
            lote=lote,
            event_type=event_type,
            description=f"Status updated to {lote.get_status_display()}",
            created_by=request.user
        )
        
        serializer = self.get_serializer(lote)
        return Response(serializer.data)
    
    @action(detail=True, methods=['POST'], url_path='add-document')
    def add_document(self, request, pk=None):
        """Add a document to a lot"""
        lote = self.get_object()
        
        # Check if user has permission (owner or admin)
        self.check_object_permissions(request, lote)
        
        # Create serializer with request data
        serializer = LoteDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(lote=lote, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoteEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset for lot events (read-only)"""
    queryset = LoteEvent.objects.all()
    serializer_class = LoteEventSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['lote', 'event_type']
    ordering = ['-timestamp']


class LoteDocumentViewSet(viewsets.ModelViewSet):
    """Viewset for lot documents"""
    queryset = LoteDocument.objects.all()
    serializer_class = LoteDocumentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['lote', 'document_type']
    search_fields = ['title']
    
    def get_permissions(self):
        """Set custom permissions for each action"""
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
