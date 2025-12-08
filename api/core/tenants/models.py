"""
Tenant & Membership Models
==========================
Multi-tenant architecture with role-based access control.
"""

import uuid
from enum import Enum
from django.db import models
from django.conf import settings


class TenantRole(str, Enum):
    """Roles within a tenant"""
    OWNER = 'OWNER'           # Full access, can delete tenant
    ADMIN = 'ADMIN'           # Manage users & settings
    ACCOUNTANT = 'ACCOUNTANT' # Full accounting access
    VIEWER = 'VIEWER'         # Read-only access

    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]

    @classmethod
    def has_write_access(cls, role: str) -> bool:
        return role in [cls.OWNER.value, cls.ADMIN.value, cls.ACCOUNTANT.value]

    @classmethod
    def has_admin_access(cls, role: str) -> bool:
        return role in [cls.OWNER.value, cls.ADMIN.value]


class Tenant(models.Model):
    """
    租戶模型 - 每個租戶代表一個獨立的公司/組織
    """
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=200, help_text="Company/Organization name")
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-friendly identifier")
    
    # Company info
    legal_name = models.CharField(max_length=300, blank=True)
    tax_id = models.CharField(max_length=50, blank=True, help_text="VAT/GST/Tax ID")
    industry = models.CharField(max_length=100, blank=True)
    
    # Address
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='HK')
    
    # Contact
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Settings
    default_currency = models.CharField(max_length=3, default='HKD')
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=1, help_text="1=January")
    timezone = models.CharField(max_length=50, default='Asia/Hong_Kong')
    
    # Subscription
    subscription_plan = models.CharField(max_length=50, default='free', choices=[
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ])
    subscription_status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'),
        ('trial', 'Trial'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ])
    max_users = models.PositiveIntegerField(default=3, help_text="Max users for plan")
    
    # Metadata
    logo_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.memberships.count()


class TenantMembership(models.Model):
    """
    租戶成員關係 - 用戶可屬於多個租戶並擁有不同角色
    """
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant_memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=TenantRole.choices(),
        default=TenantRole.VIEWER.value
    )
    
    # Permissions override (optional JSON for fine-grained control)
    custom_permissions = models.JSONField(default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invitations_sent'
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['tenant', 'user']
        ordering = ['tenant', '-role', 'user__email']
        verbose_name = 'Tenant Membership'
        verbose_name_plural = 'Tenant Memberships'

    def __str__(self):
        return f"{self.user.email} @ {self.tenant.name} ({self.role})"

    @property
    def has_write_access(self):
        return TenantRole.has_write_access(self.role)

    @property
    def has_admin_access(self):
        return TenantRole.has_admin_access(self.role)


class TenantInvitation(models.Model):
    """
    租戶邀請 - 邀請新用戶加入租戶
    """
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    role = models.CharField(
        max_length=20,
        choices=TenantRole.choices(),
        default=TenantRole.VIEWER.value
    )
    
    token = models.CharField(max_length=100, unique=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant_invitations_created'
    )
    
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Tenant Invitation'
        verbose_name_plural = 'Tenant Invitations'

    def __str__(self):
        return f"Invitation to {self.email} for {self.tenant.name}"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_expired and self.accepted_at is None
