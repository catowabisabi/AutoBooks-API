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


# =================================================================
# Financial PR & IPO Advisory Models
# =================================================================

class ListedClientStatus(str, Enum):
    """Listed client status"""
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'
    PROSPECT = 'PROSPECT'
    CHURNED = 'CHURNED'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class AnnouncementType(str, Enum):
    """Announcement type"""
    RESULTS = 'RESULTS'
    INTERIM_RESULTS = 'INTERIM_RESULTS'
    PROFIT_WARNING = 'PROFIT_WARNING'
    INSIDE_INFO = 'INSIDE_INFO'
    NOTIFIABLE_TRANSACTION = 'NOTIFIABLE_TRANSACTION'
    CONNECTED_TRANSACTION = 'CONNECTED_TRANSACTION'
    SHARE_REPURCHASE = 'SHARE_REPURCHASE'
    DIVIDEND = 'DIVIDEND'
    AGM_EGM = 'AGM_EGM'
    OTHER = 'OTHER'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class MediaSentimentType(str, Enum):
    """Media sentiment type"""
    POSITIVE = 'POSITIVE'
    NEUTRAL = 'NEUTRAL'
    NEGATIVE = 'NEGATIVE'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class IPOStageType(str, Enum):
    """IPO stage type"""
    INITIAL_CONTACT = 'INITIAL_CONTACT'
    PITCH = 'PITCH'
    MANDATE_WON = 'MANDATE_WON'
    PREPARATION = 'PREPARATION'
    A1_FILING = 'A1_FILING'
    HKEX_REVIEW = 'HKEX_REVIEW'
    SFC_REVIEW = 'SFC_REVIEW'
    HEARING = 'HEARING'
    ROADSHOW = 'ROADSHOW'
    LISTING = 'LISTING'
    POST_IPO = 'POST_IPO'
    WITHDRAWN = 'WITHDRAWN'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class DealSizeCategory(str, Enum):
    """Deal size category"""
    SMALL = 'SMALL'           # < HK$500M
    MEDIUM = 'MEDIUM'         # HK$500M - 2B
    LARGE = 'LARGE'           # HK$2B - 5B
    MEGA = 'MEGA'             # > HK$5B
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class ListedClient(BaseModel):
    """
    上市公司客戶
    Listed company clients for Financial PR
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='listed_client_records'
    )
    stock_code = models.CharField(max_length=20, help_text='Stock code e.g. 0001.HK')
    exchange = models.CharField(
        max_length=20,
        default='HKEX',
        help_text='Stock exchange: HKEX, NYSE, NASDAQ, etc.'
    )
    sector = models.CharField(max_length=100, blank=True)
    market_cap = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Market capitalization in HKD'
    )
    status = models.CharField(
        max_length=20,
        choices=ListedClientStatus.choices(),
        default=ListedClientStatus.ACTIVE.value
    )
    contract_start_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    annual_retainer = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Annual retainer fee'
    )
    primary_contact = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Listed Client'
        verbose_name_plural = 'Listed Clients'
    
    def __str__(self):
        return f"{self.company.name} ({self.stock_code})"


class Announcement(BaseModel):
    """
    公告記錄
    Corporate announcements tracking
    """
    listed_client = models.ForeignKey(
        ListedClient,
        on_delete=models.CASCADE,
        related_name='announcements'
    )
    announcement_type = models.CharField(
        max_length=30,
        choices=AnnouncementType.choices(),
        default=AnnouncementType.OTHER.value
    )
    title = models.CharField(max_length=500)
    publish_date = models.DateField()
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        default='DRAFT',
        help_text='DRAFT, IN_REVIEW, APPROVED, PUBLISHED'
    )
    handler = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_announcements'
    )
    word_count = models.IntegerField(default=0)
    languages = models.CharField(
        max_length=50,
        default='EN,TC',
        help_text='Languages: EN, TC, SC'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-publish_date', '-created_at']
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'
    
    def __str__(self):
        return f"{self.listed_client.stock_code} - {self.title[:50]}"


class MediaCoverage(BaseModel):
    """
    媒體報導記錄
    Media coverage tracking
    """
    listed_client = models.ForeignKey(
        ListedClient,
        on_delete=models.CASCADE,
        related_name='media_coverages',
        null=True,
        blank=True
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='media_coverages',
        null=True,
        blank=True
    )
    title = models.CharField(max_length=500)
    media_outlet = models.CharField(max_length=255)
    publish_date = models.DateField()
    url = models.URLField(blank=True)
    sentiment = models.CharField(
        max_length=20,
        choices=MediaSentimentType.choices(),
        default=MediaSentimentType.NEUTRAL.value
    )
    reach = models.IntegerField(
        default=0,
        help_text='Estimated audience reach'
    )
    engagement = models.IntegerField(
        default=0,
        help_text='Social media engagement count'
    )
    is_press_release = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-publish_date', '-created_at']
        verbose_name = 'Media Coverage'
        verbose_name_plural = 'Media Coverages'
    
    def __str__(self):
        return f"{self.media_outlet} - {self.title[:50]}"


class IPOMandate(BaseModel):
    """
    IPO 項目委託
    IPO mandate tracking for IPO advisory
    """
    project_name = models.CharField(max_length=255)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='ipo_mandates'
    )
    stage = models.CharField(
        max_length=30,
        choices=IPOStageType.choices(),
        default=IPOStageType.INITIAL_CONTACT.value
    )
    target_exchange = models.CharField(
        max_length=20,
        default='HKEX',
        help_text='Target exchange: HKEX, NYSE, NASDAQ, etc.'
    )
    target_board = models.CharField(
        max_length=30,
        default='MAIN',
        help_text='MAIN, GEM, etc.'
    )
    deal_size = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Expected deal size in HKD'
    )
    deal_size_category = models.CharField(
        max_length=20,
        choices=DealSizeCategory.choices(),
        default=DealSizeCategory.MEDIUM.value
    )
    fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Fee as percentage of deal size'
    )
    estimated_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    probability = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Win probability percentage'
    )
    
    # Timeline
    pitch_date = models.DateField(null=True, blank=True)
    mandate_date = models.DateField(null=True, blank=True)
    target_listing_date = models.DateField(null=True, blank=True)
    actual_listing_date = models.DateField(null=True, blank=True)
    
    # Team
    lead_partner = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_ipo_mandates'
    )
    
    # SFC tracking
    sfc_application_date = models.DateField(null=True, blank=True)
    sfc_approval_date = models.DateField(null=True, blank=True)
    is_sfc_approved = models.BooleanField(default=False)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'IPO Mandate'
        verbose_name_plural = 'IPO Mandates'
    
    def __str__(self):
        return f"{self.project_name} - {self.stage}"


class ServiceRevenue(BaseModel):
    """
    服務收入分類
    Revenue breakdown by service type
    """
    SERVICE_TYPES = [
        ('IPO_ADVISORY', 'IPO Advisory'),
        ('FINANCIAL_PR', 'Financial PR'),
        ('INVESTOR_RELATIONS', 'Investor Relations'),
        ('RESULTS_ANNOUNCEMENT', 'Results Announcement'),
        ('TRANSACTION_SUPPORT', 'Transaction Support'),
        ('CRISIS_MANAGEMENT', 'Crisis Management'),
        ('ESG_ADVISORY', 'ESG Advisory'),
        ('MEDIA_TRAINING', 'Media Training'),
        ('OTHER', 'Other'),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='service_revenues',
        null=True,
        blank=True
    )
    service_type = models.CharField(
        max_length=30,
        choices=SERVICE_TYPES,
        default='OTHER'
    )
    period_year = models.IntegerField(help_text='Year')
    period_month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text='Month (1-12)'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    billable_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-period_year', '-period_month']
        verbose_name = 'Service Revenue'
        verbose_name_plural = 'Service Revenues'
        unique_together = ['company', 'service_type', 'period_year', 'period_month']
    
    def __str__(self):
        return f"{self.service_type} - {self.period_year}/{self.period_month}"


class ActiveEngagement(BaseModel):
    """
    活躍專案
    Active client engagements
    """
    ENGAGEMENT_TYPES = [
        ('RETAINER', 'Retainer'),
        ('PROJECT', 'Project'),
        ('AD_HOC', 'Ad-hoc'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('PAUSED', 'Paused'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='engagements'
    )
    title = models.CharField(max_length=255)
    engagement_type = models.CharField(
        max_length=20,
        choices=ENGAGEMENT_TYPES,
        default='PROJECT'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    lead = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_engagements'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-start_date', '-created_at']
        verbose_name = 'Active Engagement'
        verbose_name_plural = 'Active Engagements'
    
    def __str__(self):
        return f"{self.company.name} - {self.title}"


class ClientPerformance(BaseModel):
    """
    客戶績效指標
    Client performance metrics
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='performance_records'
    )
    period_year = models.IntegerField()
    period_quarter = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    revenue_generated = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    satisfaction_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    projects_completed = models.IntegerField(default=0)
    referrals_made = models.IntegerField(default=0)
    response_time_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Average response time in hours'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-period_year', '-period_quarter']
        verbose_name = 'Client Performance'
        verbose_name_plural = 'Client Performances'
        unique_together = ['company', 'period_year', 'period_quarter']
    
    def __str__(self):
        return f"{self.company.name} - Q{self.period_quarter} {self.period_year}"


class ClientIndustry(BaseModel):
    """
    客戶行業分布
    Client industry distribution
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=7,
        default='#6366f1',
        help_text='Hex color code for charts'
    )
    client_count = models.IntegerField(default=0)
    total_revenue = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Client Industry'
        verbose_name_plural = 'Client Industries'
    
    def __str__(self):
        return self.name


class MediaSentimentRecord(BaseModel):
    """
    媒體情緒記錄
    Media sentiment tracking over time
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='sentiment_records',
        null=True,
        blank=True,
        help_text='Company this sentiment record belongs to'
    )
    period_date = models.DateField()
    positive_count = models.IntegerField(default=0)
    neutral_count = models.IntegerField(default=0)
    negative_count = models.IntegerField(default=0)
    total_reach = models.BigIntegerField(default=0)
    total_engagement = models.BigIntegerField(default=0)
    sentiment_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Overall sentiment score -100 to 100'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-period_date']
        verbose_name = 'Media Sentiment Record'
        verbose_name_plural = 'Media Sentiment Records'
    
    def __str__(self):
        return f"Sentiment {self.period_date}"




class RevenueTrend(BaseModel):
    """
    收入趨勢
    Monthly revenue trends
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='revenue_trends',
        null=True,
        blank=True,
        help_text='Company this revenue trend belongs to'
    )
    period_year = models.IntegerField()
    period_month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    total_revenue = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00')
    )
    recurring_revenue = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00')
    )
    project_revenue = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00')
    )
    new_clients = models.IntegerField(default=0)
    churned_clients = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-period_year', '-period_month']
        verbose_name = 'Revenue Trend'
        verbose_name_plural = 'Revenue Trends'
        unique_together = ['company', 'period_year', 'period_month']
    
    def __str__(self):
        return f"Revenue {self.period_year}/{self.period_month}"


# =================================================================
# IPO Project Management Models
# =================================================================

class IPOTimelineProgress(BaseModel):
    """
    IPO 項目時間線進度
    Track IPO project milestone progress (for the radial bar chart)
    """
    PHASE_CHOICES = [
        ('DUE_DILIGENCE', 'Due Diligence'),
        ('DOCUMENTATION', 'Documentation'),
        ('REGULATORY', 'Regulatory Filing'),
        ('MARKETING', 'Marketing/Roadshow'),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='ipo_timeline_progress'
    )
    ipo_mandate = models.ForeignKey(
        'IPOMandate',
        on_delete=models.CASCADE,
        related_name='timeline_progress',
        null=True,
        blank=True
    )
    phase = models.CharField(
        max_length=30,
        choices=PHASE_CHOICES,
        default='DUE_DILIGENCE'
    )
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    start_date = models.DateField(null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        default='IN_PROGRESS',
        help_text='NOT_STARTED, IN_PROGRESS, COMPLETED, DELAYED'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['company', 'phase']
        verbose_name = 'IPO Timeline Progress'
        verbose_name_plural = 'IPO Timeline Progress Records'
        unique_together = ['company', 'ipo_mandate', 'phase']
    
    def __str__(self):
        return f"{self.company.name} - {self.phase}: {self.progress_percentage}%"


class IPODealFunnel(BaseModel):
    """
    IPO 交易漏斗
    Track deal pipeline stages (for the deal funnel chart)
    """
    STAGE_CHOICES = [
        ('LEADS', 'Leads'),
        ('QUALIFIED', 'Qualified'),
        ('PROPOSAL', 'Proposal'),
        ('DUE_DILIGENCE', 'Due Diligence'),
        ('FILING', 'Filing'),
        ('LISTED', 'Listed'),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='ipo_deal_funnel'
    )
    period_date = models.DateField()
    stage = models.CharField(
        max_length=30,
        choices=STAGE_CHOICES,
        default='LEADS'
    )
    deal_count = models.IntegerField(default=0)
    conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Conversion rate to this stage (%)'
    )
    total_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00')
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-period_date', 'stage']
        verbose_name = 'IPO Deal Funnel'
        verbose_name_plural = 'IPO Deal Funnel Records'
    
    def __str__(self):
        return f"{self.stage}: {self.deal_count} deals"


class IPODealSize(BaseModel):
    """
    IPO 交易規模分佈
    Track deal size distribution (for the deal size pie chart)
    """
    SIZE_CATEGORY_CHOICES = [
        ('MEGA', 'Mega (>$1B)'),
        ('LARGE', 'Large ($500M-1B)'),
        ('MID', 'Mid ($100-500M)'),
        ('SMALL', 'Small (<$100M)'),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='ipo_deal_sizes'
    )
    period_date = models.DateField()
    size_category = models.CharField(
        max_length=20,
        choices=SIZE_CATEGORY_CHOICES,
        default='MID'
    )
    deal_count = models.IntegerField(default=0)
    total_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total deal amount in millions'
    )
    avg_deal_size = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00')
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-period_date', 'size_category']
        verbose_name = 'IPO Deal Size'
        verbose_name_plural = 'IPO Deal Size Records'
    
    def __str__(self):
        return f"{self.size_category}: {self.deal_count} deals (${self.total_amount}M)"


# =================================================================
# Partner/Collaboration Models (Updated Active Engagement)
# =================================================================

class BusinessPartner(BaseModel):
    """
    合作夥伴/KOL/服務商
    Track business partners, KOLs, and service providers
    """
    PARTNER_TYPES = [
        ('KOL', 'KOL/Influencer'),
        ('MEDIA', 'Media Partner'),
        ('AGENCY', 'Agency'),
        ('VENDOR', 'Vendor/Supplier'),
        ('CONSULTANT', 'Consultant'),
        ('LEGAL', 'Legal Firm'),
        ('FINANCIAL', 'Financial Advisor'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('PROSPECT', 'Prospect'),
        ('TERMINATED', 'Terminated'),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='business_partners'
    )
    name = models.CharField(max_length=255)
    partner_type = models.CharField(
        max_length=20,
        choices=PARTNER_TYPES,
        default='OTHER'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )
    contact_person = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    service_description = models.TextField(blank=True)
    contract_start_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    contract_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    rating = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text='Partner rating 0-5 stars'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Business Partner'
        verbose_name_plural = 'Business Partners'
    
    def __str__(self):
        return f"{self.name} ({self.partner_type})"


