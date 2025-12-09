# Tenant module
# Models should be imported from core.tenants.models directly
# to avoid circular imports and app registry issues

def get_tenant_model():
    """Lazy import of Tenant model"""
    from .models import Tenant
    return Tenant

def get_tenant_membership_model():
    """Lazy import of TenantMembership model"""
    from .models import TenantMembership
    return TenantMembership

def get_tenant_role():
    """Lazy import of TenantRole enum"""
    from .models import TenantRole
    return TenantRole

# These don't involve models, safe to import directly
from .middleware import TenantMiddleware, get_current_tenant
from .decorators import require_role, require_tenant
from .managers import TenantAwareManager

__all__ = [
    'get_tenant_model',
    'get_tenant_membership_model',
    'get_tenant_role',
    'TenantMiddleware',
    'get_current_tenant',
    'require_role',
    'require_tenant',
    'TenantAwareManager',
]
