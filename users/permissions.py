from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """Allow access only to admin users"""
    
    def has_permission(self, request, view):
        return request.user and request.user.role == 'admin'


class IsSupervisorUser(permissions.BasePermission):
    """Allow access to admin and supervisor users"""
    
    def has_permission(self, request, view):
        return request.user and request.user.role in ['admin', 'supervisor']


class IsOwnerOrAdmin(permissions.BasePermission):
    """Allow access to object owner or admin users"""
    
    def has_object_permission(self, request, view, obj):
        # Allow admin users
        if request.user.role == 'admin':
            return True
        
        # Check if object has a user field
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if object has a created_by field
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False

class IsOperatorUser(permissions.BasePermission):
    """
    Permite acceso a todos los usuarios autenticados (operadores, supervisores y administradores).
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
