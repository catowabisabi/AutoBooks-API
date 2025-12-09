"""
Tenant Middleware
=================
Sets current tenant context from request headers or user session.
"""

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext_lazy as _

from .managers import set_current_tenant, clear_current_tenant, get_current_tenant


def get_tenant_model():
    """Lazy import of Tenant model"""
    from .models import Tenant
    return Tenant


def get_membership_model():
    """Lazy import of TenantMembership model"""
    from .models import TenantMembership
    return TenantMembership


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware to set tenant context for each request.
    
    Tenant is determined by:
    1. X-Tenant-ID header (UUID)
    2. X-Tenant-Slug header (slug)
    3. User's default/last active tenant
    
    Add to MIDDLEWARE in settings.py:
        'core.tenants.middleware.TenantMiddleware',
    """
    
    # Paths that don't require tenant context
    EXEMPT_PATHS = [
        '/api/v1/auth/',
        '/api/v1/users/me/',
        '/api/v1/tenants/',  # tenant listing/creation
        '/admin/',
        '/health/',
        '/__debug__/',
    ]
    
    def process_request(self, request):
        """Set tenant context before view processing"""
        clear_current_tenant()
        request.tenant = None
        request.tenant_membership = None
        
        # Skip for exempt paths
        if self._is_exempt_path(request.path):
            return None
        
        # Skip for unauthenticated users
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        tenant, invalid_header = self._resolve_tenant(request)

        if invalid_header:
            return JsonResponse({
                'error': 'invalid_tenant_header',
                'message': _('Invalid tenant identifier provided.')
            }, status=400)

        if tenant:
            # Verify user has access to this tenant
            membership = self._get_membership(request.user, tenant)
            if membership and membership.is_active:
                set_current_tenant(tenant)
                request.tenant = tenant
                request.tenant_membership = membership

                # Prevent viewers from write operations
                if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                    from core.tenants.models import TenantRole
                    if membership.role == TenantRole.VIEWER.value:
                        return JsonResponse({
                            'error': 'write_access_required',
                            'message': _('Write access is required for this operation.')
                        }, status=403)
            elif self._is_invitation_accept_path(request.path):
                # Allow non-members to accept invitations
                set_current_tenant(tenant)
                request.tenant = tenant
            else:
                # User doesn't have access to requested tenant
                return JsonResponse({
                    'error': 'tenant_access_denied',
                    'message': _('You do not have access to this organization.')
                }, status=403)
        else:
            # Try to get user's default tenant
            default_tenant = self._get_default_tenant(request.user)
            if default_tenant:
                membership = self._get_membership(request.user, default_tenant)
                set_current_tenant(default_tenant)
                request.tenant = default_tenant
                request.tenant_membership = membership
        
        return None
    
    def process_response(self, request, response):
        """Clear tenant context after response"""
        clear_current_tenant()
        return response
    
    def _is_exempt_path(self, path):
        """Check if path is exempt from tenant requirement"""
        return any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS)
    
    def _resolve_tenant(self, request):
        """Resolve tenant from request headers"""
        Tenant = get_tenant_model()
        header_present = False

        def _get_header(name):
            # Django exposes HTTP_X_TENANT_ID in META; request.headers normalizes too
            return request.headers.get(name) or request.META.get('HTTP_' + name.upper().replace('-', '_'))

        # Try X-Tenant-ID header first
        tenant_id = _get_header('X-Tenant-ID')
        if tenant_id:
            header_present = True
            try:
                return Tenant.objects.get(id=tenant_id, is_active=True), False
            except (Tenant.DoesNotExist, ValueError):
                return None, True
        
        # Try X-Tenant-Slug header
        tenant_slug = _get_header('X-Tenant-Slug')
        if tenant_slug:
            header_present = True
            try:
                return Tenant.objects.get(slug=tenant_slug, is_active=True), False
            except Tenant.DoesNotExist:
                return None, True
        
        return (None, False) if header_present else (None, None)

    def _is_invitation_accept_path(self, path: str) -> bool:
        return 'tenant-invitations' in path and path.rstrip('/').endswith('accept')
    
    def _get_membership(self, user, tenant):
        """Get user's membership for a tenant"""
        TenantMembership = get_membership_model()
        try:
            return TenantMembership.objects.select_related('tenant').get(
                user=user,
                tenant=tenant,
                is_active=True
            )
        except TenantMembership.DoesNotExist:
            return None
    
    def _get_default_tenant(self, user):
        """Get user's default/first tenant"""
        TenantMembership = get_membership_model()
        membership = TenantMembership.objects.filter(
            user=user,
            is_active=True,
            tenant__is_active=True
        ).select_related('tenant').first()
        
        return membership.tenant if membership else None


def get_current_tenant():
    """Re-export for convenience"""
    from .managers import get_current_tenant as _get
    return _get()
