from rest_framework import permissions


ROLE_RANK = {'operator': 0, 'supervisor': 1, 'admin': 2, 'superadmin': 3}


def can_manage_user(actor, target):
    """User mutations require a strictly lower role and the actor's own site."""
    actor_rank = 3 if actor.is_superuser else ROLE_RANK.get(actor.role, -1)
    target_rank = 3 if target.is_superuser else ROLE_RANK.get(target.role, -1)
    if actor.pk == target.pk or target_rank < 0 or actor_rank <= target_rank:
        return False
    return actor_rank == 3 or bool(actor.tenant_id and actor.tenant_id == target.tenant_id)


class CanManageSubordinateUser(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.role in ['superadmin', 'admin']:
            return True
        return user.role == 'supervisor' and (
            view.action == 'partial_update' and set(request.data) == {'is_active'}
        )

    def has_object_permission(self, request, view, obj):
        return can_manage_user(request.user, obj)


class IsSuperAdminUser(permissions.BasePermission):
    """Allow access only to superadmin users or is_superuser"""
    
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and (
                request.user.role == 'superadmin' or request.user.is_superuser
            )
        )


class IsAdminUser(permissions.BasePermission):
    """Allow access to superadmin and admin users"""
    
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and (
                request.user.role in ['admin', 'superadmin'] or request.user.is_superuser
            )
        )


class IsSupervisorUser(permissions.BasePermission):
    """Allow access to admin and supervisor users"""
    
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and (
                request.user.role in ['admin', 'superadmin', 'supervisor'] or request.user.is_superuser
            )
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """Allow access to object owner or admin users"""
    
    def has_object_permission(self, request, view, obj):
        # Allow admin / superadmin users
        if request.user.is_superuser or request.user.role in ['admin', 'superadmin']:
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
