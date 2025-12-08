"""
Tenant & Role Decorators
========================
Decorators for enforcing tenant context and role-based access.
"""

from functools import wraps
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import status

from .models import TenantRole
from .managers import get_current_tenant


def require_tenant(view_func):
    """
    Decorator to require a valid tenant context.
    
    Usage:
        @require_tenant
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'tenant') or request.tenant is None:
            return JsonResponse({
                'error': 'tenant_required',
                'message': _('A valid tenant context is required for this operation.')
            }, status=status.HTTP_400_BAD_REQUEST)
        return view_func(request, *args, **kwargs)
    return wrapper


def require_role(*allowed_roles):
    """
    Decorator to require specific role(s) within tenant.
    
    Usage:
        @require_role(TenantRole.OWNER, TenantRole.ADMIN)
        def admin_only_view(request):
            ...
        
        @require_role('ACCOUNTANT', 'ADMIN', 'OWNER')
        def accounting_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # First check tenant context
            if not hasattr(request, 'tenant') or request.tenant is None:
                return JsonResponse({
                    'error': 'tenant_required',
                    'message': _('A valid tenant context is required.')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check membership exists
            if not hasattr(request, 'tenant_membership') or request.tenant_membership is None:
                return JsonResponse({
                    'error': 'membership_required',
                    'message': _('You are not a member of this organization.')
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Normalize roles to strings
            normalized_roles = []
            for role in allowed_roles:
                if isinstance(role, TenantRole):
                    normalized_roles.append(role.value)
                else:
                    normalized_roles.append(str(role))
            
            # Check role
            user_role = request.tenant_membership.role
            if user_role not in normalized_roles:
                return JsonResponse({
                    'error': 'insufficient_permissions',
                    'message': _('You do not have permission to perform this action.'),
                    'required_roles': normalized_roles,
                    'your_role': user_role
                }, status=status.HTTP_403_FORBIDDEN)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_write_access(view_func):
    """
    Decorator to require write access (OWNER, ADMIN, or ACCOUNTANT).
    
    Usage:
        @require_write_access
        def create_invoice(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'tenant_membership') or request.tenant_membership is None:
            return JsonResponse({
                'error': 'membership_required',
                'message': _('You are not a member of this organization.')
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not request.tenant_membership.has_write_access:
            return JsonResponse({
                'error': 'write_access_required',
                'message': _('Write access is required for this operation.')
            }, status=status.HTTP_403_FORBIDDEN)
        
        return view_func(request, *args, **kwargs)
    return wrapper


def require_admin_access(view_func):
    """
    Decorator to require admin access (OWNER or ADMIN).
    
    Usage:
        @require_admin_access
        def manage_users(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'tenant_membership') or request.tenant_membership is None:
            return JsonResponse({
                'error': 'membership_required',
                'message': _('You are not a member of this organization.')
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not request.tenant_membership.has_admin_access:
            return JsonResponse({
                'error': 'admin_access_required',
                'message': _('Admin access is required for this operation.')
            }, status=status.HTTP_403_FORBIDDEN)
        
        return view_func(request, *args, **kwargs)
    return wrapper


class TenantRolePermission:
    """
    DRF Permission class for role-based access control.
    
    Usage in ViewSet:
        permission_classes = [IsAuthenticated, TenantRolePermission]
        required_roles = [TenantRole.OWNER, TenantRole.ADMIN]
    """
    
    def __init__(self, allowed_roles=None):
        self.allowed_roles = allowed_roles or []
    
    def has_permission(self, request, view):
        # Check tenant context
        if not hasattr(request, 'tenant') or request.tenant is None:
            return False
        
        # Check membership
        if not hasattr(request, 'tenant_membership') or request.tenant_membership is None:
            return False
        
        # If no specific roles required, just check membership
        if not self.allowed_roles:
            return True
        
        # Check role
        user_role = request.tenant_membership.role
        normalized_roles = [
            r.value if isinstance(r, TenantRole) else str(r)
            for r in self.allowed_roles
        ]
        
        return user_role in normalized_roles
    
    def has_object_permission(self, request, view, obj):
        # For object-level, also check tenant matches
        if hasattr(obj, 'tenant'):
            return obj.tenant == request.tenant
        return True
