"""
Analytics Models
================
Dashboard, Charts, and Sales Analytics for ERP reporting.
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

from core.models import BaseModel


class Dashboard(models.Model):
    """Analytics dashboards"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    layout = models.JSONField(default=dict, blank=True, help_text='Dashboard layout configuration')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return self.title


class Chart(models.Model):
    """Charts within dashboards"""
    CHART_TYPES = (
        ('bar', 'Bar'),
        ('pie', 'Pie'),
        ('line', 'Line'),
        ('scatter', 'Scatter'),
        ('area', 'Area'),
        ('donut', 'Donut'),
        ('radar', 'Radar'),
        ('table', 'Table'),
        ('metric', 'Metric Card'),
        ('unsupported', 'Unsupported'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='charts')
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=CHART_TYPES)
    config = models.JSONField(default=dict)
    data_source = models.CharField(max_length=100, blank=True, help_text='API endpoint or data source name')
    position = models.IntegerField(default=0, help_text='Position in dashboard')
    width = models.IntegerField(default=6, validators=[MinValueValidator(1), MaxValueValidator(12)])
    height = models.IntegerField(default=300)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"


class AnalyticsSales(BaseModel):
    """
    銷售分析數據
    Monthly sales analytics and KPIs
    """
    year = models.IntegerField()
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    
    # Revenue metrics
    revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total revenue for the month'
    )
    target_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Revenue target for the month'
    )
    growth_percentage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Month-over-month growth percentage'
    )
    yoy_growth = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Year-over-year growth percentage'
    )
    
    # Client metrics
    new_clients = models.IntegerField(default=0, help_text='Number of new clients acquired')
    total_clients = models.IntegerField(default=0, help_text='Total active clients')
    churned_clients = models.IntegerField(default=0, help_text='Clients lost this month')
    churn_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Client churn rate percentage'
    )
    
    # Performance metrics
    deals_closed = models.IntegerField(default=0)
    deals_pipeline = models.IntegerField(default=0)
    average_deal_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Lead to client conversion rate'
    )
    
    # Cost metrics
    operating_costs = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    marketing_spend = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['year', 'month']
        ordering = ['-year', '-month']
        verbose_name = 'Sales Analytics'
        verbose_name_plural = 'Sales Analytics'
    
    @property
    def month_name(self):
        """Return month name"""
        import calendar
        return calendar.month_name[self.month]
    
    @property
    def profit_margin(self):
        """Calculate profit margin"""
        if self.revenue > 0:
            return ((self.revenue - self.operating_costs) / self.revenue) * 100
        return Decimal('0.00')
    
    @property
    def revenue_achievement(self):
        """Calculate revenue target achievement percentage"""
        if self.target_revenue > 0:
            return (self.revenue / self.target_revenue) * 100
        return Decimal('0.00')
    
    def __str__(self):
        return f"{self.year}-{self.month:02d} Sales Analytics"


class KPIMetric(BaseModel):
    """
    Key Performance Indicators tracking
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=50,
        default='GENERAL',
        help_text='FINANCIAL, OPERATIONAL, SALES, HR, etc.'
    )
    
    # Current values
    current_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    target_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    previous_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    
    # Display settings
    unit = models.CharField(max_length=20, blank=True, help_text='%, $, units, etc.')
    display_format = models.CharField(
        max_length=20,
        default='NUMBER',
        help_text='NUMBER, CURRENCY, PERCENTAGE'
    )
    trend = models.CharField(
        max_length=10,
        default='NEUTRAL',
        help_text='UP, DOWN, NEUTRAL'
    )
    is_positive_good = models.BooleanField(
        default=True,
        help_text='True if higher value is better'
    )
    
    # Time tracking
    period = models.CharField(max_length=20, blank=True, help_text='2024-Q4, 2024-12, etc.')
    
    class Meta:
        ordering = ['category', 'name']
    
    @property
    def achievement_percentage(self):
        if self.target_value > 0:
            return (self.current_value / self.target_value) * 100
        return Decimal('0')
    
    @property
    def change_percentage(self):
        if self.previous_value > 0:
            return ((self.current_value - self.previous_value) / self.previous_value) * 100
        return Decimal('0')
    
    def __str__(self):
        return f"{self.name}: {self.current_value}{self.unit}"


class ReportSchedule(BaseModel):
    """Scheduled report generation"""
    name = models.CharField(max_length=255)
    report_type = models.CharField(
        max_length=50,
        help_text='SALES, FINANCIAL, HR, AUDIT, etc.'
    )
    frequency = models.CharField(
        max_length=20,
        default='MONTHLY',
        help_text='DAILY, WEEKLY, MONTHLY, QUARTERLY, ANNUALLY'
    )
    recipients = models.JSONField(default=list, help_text='List of email addresses')
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    config = models.JSONField(default=dict, help_text='Report configuration')
    
    def __str__(self):
        return f"{self.name} ({self.frequency})"

