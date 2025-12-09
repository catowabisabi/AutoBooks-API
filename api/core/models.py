import uuid
from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


# Lazy imports to avoid circular dependencies and app registry issues
# Import these from core.tenants.models directly when needed
def get_tenant_models():
    """Lazy import of tenant models"""
    from core.tenants.models import Tenant, TenantMembership, TenantInvitation, TenantRole
    return Tenant, TenantMembership, TenantInvitation, TenantRole


def get_tenant_aware_model():
    """Lazy import of TenantAwareModel"""
    from core.tenants.base import TenantAwareModel
    return TenantAwareModel


def get_tenant_manager():
    """Lazy import of TenantAwareManager"""
    from core.tenants.managers import TenantAwareManager
    return TenantAwareManager


# Re-export manager functions (these don't import models)
from core.tenants.managers import get_current_tenant, set_current_tenant

__all__ = [
    'BaseModel',
    'get_tenant_models',
    'get_tenant_aware_model',
    'get_tenant_manager',
    'get_current_tenant',
    'set_current_tenant',
]
