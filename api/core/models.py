import uuid
from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


# Import tenant models for easy access
from core.tenants.models import Tenant, TenantMembership, TenantInvitation, TenantRole
from core.tenants.base import TenantAwareModel
from core.tenants.managers import TenantAwareManager, get_current_tenant, set_current_tenant

__all__ = [
    'BaseModel',
    'Tenant',
    'TenantMembership',
    'TenantInvitation',
    'TenantRole',
    'TenantAwareModel',
    'TenantAwareManager',
    'get_current_tenant',
    'set_current_tenant',
]
