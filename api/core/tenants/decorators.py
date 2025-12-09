"""
Tenant & Role Decorators
========================
Decorators for enforcing tenant context and role-based access.
"""

from functools import wraps
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import status

from .managers import get_current_tenant


def get_tenant_role():
    """Lazy import of TenantRole"""
    from .models import TenantRole
    return TenantRole


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
            TenantRole = get_tenant_role()
            
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
        TenantRole = get_tenant_role()
        
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


class TenantAccessPermission:
    """
    DRF Permission class that resolves tenant from headers and enforces access.
    This runs after DRF authentication, so it works with force_authenticate.
    
    Usage in ViewSet:
        permission_classes = [IsAuthenticated, TenantAccessPermission]
    """
    
    def has_permission(self, request, view):
        from .models import Tenant, TenantMembership, TenantRole
        from .managers import set_current_tenant
        
        # Already set by middleware?
        if getattr(request, 'tenant', None) and getattr(request, 'tenant_membership', None):
            # Still check viewer write restriction
            return self._check_write_access(request)
        
        # Resolve tenant from headers
        tenant = self._resolve_tenant(request)
        if tenant is None:
            # Check if header was provided but invalid
            tenant_header = request.META.get('HTTP_X_TENANT_ID') or request.META.get('HTTP_X_TENANT_SLUG')
            if tenant_header:
                # Invalid tenant header
                return False
            # No header - try default tenant
            tenant = self._get_default_tenant(request.user)
        
        if tenant is None:
            # No tenant context available
            return False
        
        # Get membership
        membership = self._get_membership(request.user, tenant)
        if membership is None:
            return False
        
        # Set on request
        request.tenant = tenant
        request.tenant_membership = membership
        set_current_tenant(tenant)
        
        return self._check_write_access(request)
    
    def _check_write_access(self, request):
        from .models import TenantRole
        
        membership = getattr(request, 'tenant_membership', None)
        if membership and request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            if membership.role == TenantRole.VIEWER.value:
                return False
        return True
    
    def _resolve_tenant(self, request):
        from .models import Tenant
        
        tenant_id = request.META.get('HTTP_X_TENANT_ID') or request.headers.get('X-Tenant-ID')
        if tenant_id:
            try:
                return Tenant.objects.get(id=tenant_id, is_active=True)
            except Exception:
                return None
        
        tenant_slug = request.META.get('HTTP_X_TENANT_SLUG') or request.headers.get('X-Tenant-Slug')
        if tenant_slug:
            try:
                return Tenant.objects.get(slug=tenant_slug, is_active=True)
            except Tenant.DoesNotExist:
                return None
        
        return None
    
    def _get_membership(self, user, tenant):
        from .models import TenantMembership
        try:
            return TenantMembership.objects.get(user=user, tenant=tenant, is_active=True)
        except TenantMembership.DoesNotExist:
            return None
    
    def _get_default_tenant(self, user):
        from .models import TenantMembership
        membership = TenantMembership.objects.filter(
            user=user, is_active=True, tenant__is_active=True
        ).select_related('tenant').first()
        return membership.tenant if membership else None
