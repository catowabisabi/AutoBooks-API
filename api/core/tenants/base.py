"""
Tenant-Aware Base Model
=======================
Abstract base model that includes tenant FK for multi-tenant isolation.
"""

import uuid
from django.db import models

from .managers import TenantAwareManager, UnscopedManager


class TenantAwareModel(models.Model):
    """
    Abstract base model for tenant-scoped data.
    
    All models that need tenant isolation should inherit from this.
    
    Usage:
        class Invoice(TenantAwareModel):
            ...
            
            # Automatic tenant scoping (default)
            objects = TenantAwareManager()
            
            # Unscoped access for admin
            all_objects = UnscopedManager()
    """
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
        help_text='Owning tenant/organization'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Default manager with tenant scoping
    objects = TenantAwareManager()
    # Unscoped manager for admin/cross-tenant operations
    all_objects = UnscopedManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Auto-set tenant from context if not provided"""
        if not self.tenant_id:
            from .managers import get_current_tenant
            tenant = get_current_tenant()
            if tenant:
                self.tenant = tenant
        super().save(*args, **kwargs)
