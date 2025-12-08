"""
Tenant-Aware QuerySet Managers
==============================
Automatically scope queries to the current tenant context.
"""

from django.db import models
from threading import local

# Thread-local storage for current tenant
_thread_locals = local()


def get_current_tenant():
    """Get current tenant from thread-local storage"""
    return getattr(_thread_locals, 'tenant', None)


def set_current_tenant(tenant):
    """Set current tenant in thread-local storage"""
    _thread_locals.tenant = tenant


def clear_current_tenant():
    """Clear current tenant from thread-local storage"""
    if hasattr(_thread_locals, 'tenant'):
        del _thread_locals.tenant


class TenantAwareQuerySet(models.QuerySet):
    """QuerySet that automatically filters by tenant"""
    
    def for_tenant(self, tenant):
        """Filter queryset by specific tenant"""
        if tenant is None:
            return self.none()
        return self.filter(tenant=tenant)
    
    def for_current_tenant(self):
        """Filter queryset by current tenant from thread-local"""
        tenant = get_current_tenant()
        if tenant is None:
            return self.none()
        return self.filter(tenant=tenant)


class TenantAwareManager(models.Manager):
    """
    Manager that auto-scopes queries to current tenant.
    
    Usage:
        class MyModel(TenantAwareModel):
            objects = TenantAwareManager()
            all_objects = models.Manager()  # bypass tenant filter
    """
    
    def get_queryset(self):
        qs = TenantAwareQuerySet(self.model, using=self._db)
        tenant = get_current_tenant()
        if tenant is not None:
            return qs.filter(tenant=tenant)
        return qs
    
    def unscoped(self):
        """Return unscoped queryset (bypass tenant filter)"""
        return TenantAwareQuerySet(self.model, using=self._db)
    
    def for_tenant(self, tenant):
        """Explicitly scope to a specific tenant"""
        return TenantAwareQuerySet(self.model, using=self._db).for_tenant(tenant)


class UnscopedManager(models.Manager):
    """Manager that does NOT auto-scope to tenant (for admin/superuser views)"""
    
    def get_queryset(self):
        return TenantAwareQuerySet(self.model, using=self._db)
