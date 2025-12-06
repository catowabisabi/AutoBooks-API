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
