from enum import Enum
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission
from django.db import models
from hrms.models import Designation, Department
from core.models import BaseModel


class EmployeeType(str, Enum):
    ADMIN = 'ADMIN'
    FULL_TIME = 'FULL_TIME'
    PART_TIME = 'PART_TIME'
    CONTRACTOR = 'CONTRACTOR'
    INTERN = 'INTERN'

    @classmethod
    def choices(cls):
        return [(tag, tag.value) for tag in cls]


class UserManager(BaseUserManager):
    def create_user(self, email=None, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        return self.create_user(email, password, **extra_fields)


class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN'
        USER = 'USER'

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.USER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Profile fields
    phone = models.CharField(max_length=50, blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    timezone = models.CharField(max_length=50, default='Asia/Hong_Kong')
    language = models.CharField(max_length=10, default='en')

    designation = models.ForeignKey(Designation, on_delete=models.PROTECT, related_name='users', null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='users', null=True, blank=True)
    manager = models.ForeignKey('User', on_delete=models.PROTECT, related_name='subordinates', null=True, blank=True)
    employee_type = models.CharField(
        max_length=20,
        choices=EmployeeType.choices(),
        default=EmployeeType.FULL_TIME.value,
        help_text='Type of employee (e.g., Full-Time, Part-Time, Contractor, Intern)'
    )

    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_groups',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class UserSettings(BaseModel):
    """User settings including billing and notifications"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    
    # Notification Settings
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    # Notification Types
    notify_task_assigned = models.BooleanField(default=True)
    notify_task_completed = models.BooleanField(default=True)
    notify_invoice_received = models.BooleanField(default=True)
    notify_payment_due = models.BooleanField(default=True)
    notify_system_updates = models.BooleanField(default=True)
    notify_security_alerts = models.BooleanField(default=True)
    notify_weekly_digest = models.BooleanField(default=False)
    notify_monthly_report = models.BooleanField(default=True)
    
    # Billing Settings
    billing_email = models.EmailField(blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    billing_city = models.CharField(max_length=100, blank=True, null=True)
    billing_country = models.CharField(max_length=100, blank=True, null=True)
    billing_postal_code = models.CharField(max_length=20, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Subscription Info
    subscription_plan = models.CharField(max_length=50, default='free', choices=[
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ])
    subscription_status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('past_due', 'Past Due'),
        ('trial', 'Trial'),
    ])
    subscription_start_date = models.DateField(blank=True, null=True)
    subscription_end_date = models.DateField(blank=True, null=True)
    
    # Payment Method
    payment_method_type = models.CharField(max_length=50, blank=True, null=True, choices=[
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
    ])
    payment_method_last_four = models.CharField(max_length=4, blank=True, null=True)
    payment_method_expiry = models.CharField(max_length=7, blank=True, null=True)  # MM/YYYY

    class Meta:
        verbose_name = 'User Settings'
        verbose_name_plural = 'User Settings'

    def __str__(self):
        return f"Settings for {self.user.email}"


class SubscriptionPlan(BaseModel):
    """Subscription Plan model for membership tiers"""
    class PlanType(models.TextChoices):
        FREE = 'free', 'Free'
        PRO = 'pro', 'Pro'
        PRO_PLUS = 'pro_plus', 'Pro+ Enterprise'
    
    class BillingCycle(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        YEARLY = 'yearly', 'Yearly'
    
    # Plan Identification
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100, help_text='English name')
    name_zh = models.CharField(max_length=100, help_text='Chinese name')
    plan_type = models.CharField(max_length=20, choices=PlanType.choices, unique=True)
    
    # Description
    description = models.TextField(blank=True)
    description_en = models.TextField(blank=True, help_text='English description')
    description_zh = models.TextField(blank=True, help_text='Chinese description')
    
    # Pricing
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    
    # Features & Limits
    max_users = models.IntegerField(default=1, help_text='Maximum number of users')
    max_companies = models.IntegerField(default=1, help_text='Maximum number of companies')
    max_storage_gb = models.IntegerField(default=1, help_text='Maximum storage in GB')
    max_documents = models.IntegerField(default=100, help_text='Maximum number of documents')
    max_invoices_monthly = models.IntegerField(default=10, help_text='Maximum invoices per month')
    max_employees = models.IntegerField(default=5, help_text='Maximum employees in HRMS')
    max_projects = models.IntegerField(default=3, help_text='Maximum active projects')
    
    # Feature Flags
    has_ai_assistant = models.BooleanField(default=False)
    has_advanced_analytics = models.BooleanField(default=False)
    has_custom_reports = models.BooleanField(default=False)
    has_api_access = models.BooleanField(default=False)
    has_priority_support = models.BooleanField(default=False)
    has_sso = models.BooleanField(default=False, help_text='Single Sign-On')
    has_audit_logs = models.BooleanField(default=False)
    has_data_export = models.BooleanField(default=True)
    has_multi_currency = models.BooleanField(default=False)
    has_custom_branding = models.BooleanField(default=False)
    
    # RAG & AI Limits
    ai_queries_monthly = models.IntegerField(default=0, help_text='AI queries per month (0=unlimited)')
    rag_documents = models.IntegerField(default=0, help_text='RAG knowledge base documents')
    
    # Status
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False, help_text='Show as popular/recommended')
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order', 'price_monthly']
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'
    
    def __str__(self):
        return f"{self.name} ({self.plan_type})"


class UserSubscription(BaseModel):
    """Track user subscriptions"""
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CANCELLED = 'cancelled', 'Cancelled'
        EXPIRED = 'expired', 'Expired'
        TRIAL = 'trial', 'Trial'
        PAST_DUE = 'past_due', 'Past Due'
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIAL)
    billing_cycle = models.CharField(
        max_length=10, 
        choices=SubscriptionPlan.BillingCycle.choices, 
        default=SubscriptionPlan.BillingCycle.MONTHLY
    )
    
    # Dates
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    trial_end_date = models.DateField(null=True, blank=True)
    next_billing_date = models.DateField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Payment
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name = 'User Subscription'
        verbose_name_plural = 'User Subscriptions'
    
    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status})"
