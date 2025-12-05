"""
Business Operations Models
==========================
Models for Audits, Tax Returns, Billable Hours, Revenue Tracking, and BMI IPO/PR Records.
"""

import uuid
from enum import Enum
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import BaseModel


# =================================================================
# Enums
# =================================================================

class AuditStatus(str, Enum):
    """Audit project status"""
    NOT_STARTED = 'NOT_STARTED'
    PLANNING = 'PLANNING'
    FIELDWORK = 'FIELDWORK'
    REVIEW = 'REVIEW'
    REPORTING = 'REPORTING'
    COMPLETED = 'COMPLETED'
    ON_HOLD = 'ON_HOLD'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class TaxReturnStatus(str, Enum):
    """Tax return case status"""
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    UNDER_REVIEW = 'UNDER_REVIEW'
    SUBMITTED = 'SUBMITTED'
    ACCEPTED = 'ACCEPTED'
    REJECTED = 'REJECTED'
    AMENDED = 'AMENDED'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class EmployeeRole(str, Enum):
    """Employee role for billable hours rate calculation"""
    CLERK = 'CLERK'           # 1x multiplier
    ACCOUNTANT = 'ACCOUNTANT' # 5x multiplier
    MANAGER = 'MANAGER'       # 3x multiplier
    DIRECTOR = 'DIRECTOR'     # 10x multiplier
    PARTNER = 'PARTNER'       # 15x multiplier
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]
    
    @classmethod
    def get_multiplier(cls, role):
        multipliers = {
            'CLERK': Decimal('1.0'),
            'ACCOUNTANT': Decimal('5.0'),
            'MANAGER': Decimal('3.0'),
            'DIRECTOR': Decimal('10.0'),
            'PARTNER': Decimal('15.0'),
        }
        return multipliers.get(role, Decimal('1.0'))


class RevenueStatus(str, Enum):
    """Revenue payment status"""
    PENDING = 'PENDING'
    PARTIAL = 'PARTIAL'
    RECEIVED = 'RECEIVED'
    OVERDUE = 'OVERDUE'
    WRITTEN_OFF = 'WRITTEN_OFF'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class BMIStage(str, Enum):
    """BMI IPO/PR project stage"""
    INITIAL_ASSESSMENT = 'INITIAL_ASSESSMENT'
    DUE_DILIGENCE = 'DUE_DILIGENCE'
    DOCUMENTATION = 'DOCUMENTATION'
    REGULATORY_FILING = 'REGULATORY_FILING'
    MARKETING = 'MARKETING'
    PRICING = 'PRICING'
    LISTING = 'LISTING'
    POST_IPO = 'POST_IPO'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class BMIStatus(str, Enum):
    """BMI project status"""
    ACTIVE = 'ACTIVE'
    ON_TRACK = 'ON_TRACK'
    DELAYED = 'DELAYED'
    AT_RISK = 'AT_RISK'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


# =================================================================
# Models
# =================================================================

class Company(BaseModel):
    """Client company for multi-tenant support"""
    name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    contact_person = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = 'Companies'
    
    def __str__(self):
        return self.name


class AuditProject(BaseModel):
    """
    審計專案管理
    Audit project tracking for accounting firms
    """
    company = models.ForeignKey(
        Company, 
        on_delete=models.PROTECT, 
        related_name='audit_projects'
    )
    fiscal_year = models.CharField(max_length=20, help_text='e.g., 2024, 2024-Q1')
    audit_type = models.CharField(
        max_length=50, 
        default='FINANCIAL',
        help_text='FINANCIAL, TAX, INTERNAL, COMPLIANCE'
    )
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Progress percentage 0-100'
    )
    status = models.CharField(
        max_length=20,
        choices=AuditStatus.choices(),
        default=AuditStatus.NOT_STARTED.value
    )
    start_date = models.DateField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_audits'
    )
    team_members = models.ManyToManyField(
        'users.User',
        related_name='audit_team_memberships',
        blank=True
    )
    budget_hours = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text='Budgeted hours for this audit'
    )
    actual_hours = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text='Actual hours spent'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company.name} - {self.fiscal_year} Audit"


class TaxReturnCase(BaseModel):
    """
    稅務申報案件
    Tax return case management
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='tax_returns'
    )
    tax_year = models.CharField(max_length=20, help_text='e.g., 2024')
    tax_type = models.CharField(
        max_length=50,
        default='PROFITS_TAX',
        help_text='PROFITS_TAX, SALARIES_TAX, PROPERTY_TAX, STAMP_DUTY'
    )
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Progress percentage 0-100'
    )
    status = models.CharField(
        max_length=20,
        choices=TaxReturnStatus.choices(),
        default=TaxReturnStatus.PENDING.value
    )
    deadline = models.DateField(null=True, blank=True)
    submitted_date = models.DateField(null=True, blank=True)
    handler = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_tax_returns'
    )
    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Calculated tax amount'
    )
    documents_received = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-deadline', '-created_at']
    
    def __str__(self):
        return f"{self.company.name} - {self.tax_year} {self.tax_type}"


class BillableHour(BaseModel):
    """
    計費時數管理
    Track billable hours by employee and role
    """
    employee = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='billable_hours'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='billable_hours',
        null=True,
        blank=True,
        help_text='Client company being billed'
    )
    project_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text='Reference to audit/tax return or other project'
    )
    role = models.CharField(
        max_length=20,
        choices=EmployeeRole.choices(),
        default=EmployeeRole.CLERK.value
    )
    base_hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('100.00'),
        help_text='Base hourly rate before multiplier'
    )
    hourly_rate_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.0'),
        help_text='Rate multiplier based on role'
    )
    date = models.DateField()
    actual_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Hours worked'
    )
    description = models.TextField(blank=True, help_text='Work description')
    is_billable = models.BooleanField(default=True)
    is_invoiced = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-date', '-created_at']
    
    @property
    def effective_rate(self):
        """Calculate effective hourly rate"""
        return self.base_hourly_rate * self.hourly_rate_multiplier
    
    @property
    def total_cost(self):
        """Calculate total cost for this entry"""
        return self.effective_rate * self.actual_hours
    
    def save(self, *args, **kwargs):
        # Auto-set multiplier based on role if not explicitly set
        if self.hourly_rate_multiplier == Decimal('1.0'):
            self.hourly_rate_multiplier = EmployeeRole.get_multiplier(self.role)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.date} ({self.actual_hours}h)"


class Revenue(BaseModel):
    """
    收入管理
    Revenue and payment tracking
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='revenues'
    )
    invoice_number = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    received_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    status = models.CharField(
        max_length=20,
        choices=RevenueStatus.choices(),
        default=RevenueStatus.PENDING.value
    )
    invoice_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    
    # Contact information
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Revenues'
    
    @property
    def pending_amount(self):
        """Calculate pending amount"""
        return self.total_amount - self.received_amount
    
    @property
    def is_fully_paid(self):
        """Check if fully paid"""
        return self.received_amount >= self.total_amount
    
    def __str__(self):
        return f"{self.company.name} - {self.invoice_number or 'No Invoice'}"


class BMIIPOPRRecord(BaseModel):
    """
    BMI IPO/PR 專案記錄
    Track BMI IPO (Initial Public Offering) and PR (Placing & Rights) projects
    """
    project_name = models.CharField(max_length=255)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='bmi_projects'
    )
    stage = models.CharField(
        max_length=30,
        choices=BMIStage.choices(),
        default=BMIStage.INITIAL_ASSESSMENT.value
    )
    status = models.CharField(
        max_length=20,
        choices=BMIStatus.choices(),
        default=BMIStatus.ACTIVE.value
    )
    project_type = models.CharField(
        max_length=20,
        default='IPO',
        help_text='IPO, PR, RIGHTS_ISSUE, PLACEMENT'
    )
    
    # Financial details
    estimated_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Estimated deal value'
    )
    total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total project cost'
    )
    
    # Timeline
    start_date = models.DateField(null=True, blank=True)
    target_completion_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)
    
    # Progress
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Team
    lead_manager = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_bmi_projects'
    )
    team_members = models.ManyToManyField(
        'users.User',
        related_name='bmi_team_memberships',
        blank=True
    )
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'BMI IPO/PR Record'
        verbose_name_plural = 'BMI IPO/PR Records'
    
    def __str__(self):
        return f"{self.project_name} ({self.project_type})"


class BMIDocument(BaseModel):
    """Documents attached to BMI projects"""
    bmi_project = models.ForeignKey(
        BMIIPOPRRecord,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    file_name = models.CharField(max_length=255)
    file_path = models.TextField()
    file_type = models.CharField(max_length=50, blank=True)
    file_size = models.BigIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.file_name} - {self.bmi_project.project_name}"
