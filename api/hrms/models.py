"""
HRMS (Human Resource Management System) Models
===============================================
Complete HR management including employees, departments, leaves, and payroll.
"""

from enum import Enum
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import BaseModel


# =================================================================
# Enums
# =================================================================

class EmploymentStatus(str, Enum):
    ACTIVE = 'ACTIVE'
    ON_LEAVE = 'ON_LEAVE'
    SUSPENDED = 'SUSPENDED'
    RESIGNED = 'RESIGNED'
    TERMINATED = 'TERMINATED'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class EmploymentType(str, Enum):
    FULL_TIME = 'FULL_TIME'
    PART_TIME = 'PART_TIME'
    CONTRACT = 'CONTRACT'
    INTERN = 'INTERN'
    PROBATION = 'PROBATION'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class LeaveTypes(str, Enum):
    SICK = "SICK"
    CASUAL = "CASUAL"
    EARNED = "EARNED"
    MATERNITY = "MATERNITY"
    PATERNITY = "PATERNITY"
    UNPAID = "UNPAID"
    COMPASSIONATE = "COMPASSIONATE"
    STUDY = "STUDY"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class LeaveStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class PayrollStatus(str, Enum):
    DRAFT = 'DRAFT'
    PENDING_APPROVAL = 'PENDING_APPROVAL'
    APPROVED = 'APPROVED'
    PROCESSING = 'PROCESSING'
    PAID = 'PAID'
    CANCELLED = 'CANCELLED'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class PaymentFrequency(str, Enum):
    WEEKLY = 'WEEKLY'
    BI_WEEKLY = 'BI_WEEKLY'
    SEMI_MONTHLY = 'SEMI_MONTHLY'
    MONTHLY = 'MONTHLY'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


# =================================================================
# Core HR Models
# =================================================================

class Designation(BaseModel):
    """Job titles/positions"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text='Hierarchy level 1-10'
    )
    
    class Meta:
        ordering = ['level', 'name']
    
    def __str__(self):
        return self.name


class Department(BaseModel):
    """Company departments"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=20, blank=True, help_text='Department code')
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_departments'
    )
    manager = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments'
    )
    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Annual department budget'
    )
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Employee(BaseModel):
    """
    Employee master data
    Links to User model for authentication
    """
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='employee_profile'
    )
    employee_id = models.CharField(max_length=50, unique=True, help_text='Employee ID/Code')
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees'
    )
    designation = models.ForeignKey(
        Designation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees'
    )
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_reports'
    )
    
    # Employment details
    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices(),
        default=EmploymentStatus.ACTIVE.value
    )
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices(),
        default=EmploymentType.FULL_TIME.value
    )
    hire_date = models.DateField(null=True, blank=True)
    probation_end_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    
    # Personal information
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    id_number = models.CharField(max_length=50, blank=True, help_text='National ID/Passport')
    phone = models.CharField(max_length=50, blank=True)
    personal_email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=50, blank=True)
    
    # Compensation
    base_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Monthly base salary'
    )
    payment_frequency = models.CharField(
        max_length=20,
        choices=PaymentFrequency.choices(),
        default=PaymentFrequency.MONTHLY.value
    )
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=100, blank=True)
    
    # Leave balances
    annual_leave_balance = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal('14.0')
    )
    sick_leave_balance = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal('10.0')
    )
    
    class Meta:
        ordering = ['employee_id']
    
    def __str__(self):
        return f"{self.employee_id} - {self.user.full_name}"


class LeaveApplication(BaseModel):
    """Employee leave requests"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='leave_applications'
    )
    leave_type = models.CharField(
        max_length=20,
        choices=LeaveTypes.choices(),
        default=LeaveTypes.CASUAL.value
    )
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal('1.0')
    )
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=LeaveStatus.choices(),
        default=LeaveStatus.PENDING.value
    )
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employee.user.full_name} - {self.leave_type} ({self.start_date} to {self.end_date})"


class LeaveBalance(BaseModel):
    """Track leave balances by type per employee per year"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_balances'
    )
    year = models.IntegerField()
    leave_type = models.CharField(
        max_length=20,
        choices=LeaveTypes.choices()
    )
    entitled_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))
    carried_over = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))
    
    class Meta:
        unique_together = ['employee', 'year', 'leave_type']
    
    @property
    def remaining_days(self):
        return self.entitled_days + self.carried_over - self.used_days
    
    def __str__(self):
        return f"{self.employee.employee_id} - {self.leave_type} ({self.year})"


# =================================================================
# Payroll Models
# =================================================================

class PayrollPeriod(BaseModel):
    """Payroll processing periods"""
    name = models.CharField(max_length=100, help_text='e.g., January 2024')
    year = models.IntegerField()
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    start_date = models.DateField()
    end_date = models.DateField()
    payment_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=PayrollStatus.choices(),
        default=PayrollStatus.DRAFT.value
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['year', 'month']
        ordering = ['-year', '-month']
    
    def __str__(self):
        return self.name


class Payroll(BaseModel):
    """Individual employee payroll records"""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='payrolls'
    )
    period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.PROTECT,
        related_name='payroll_records'
    )
    status = models.CharField(
        max_length=20,
        choices=PayrollStatus.choices(),
        default=PayrollStatus.DRAFT.value
    )
    
    # Earnings
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    overtime_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    other_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    
    # Deductions
    tax_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    mpf_employee = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0'),
        help_text='Employee MPF contribution'
    )
    mpf_employer = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0'),
        help_text='Employer MPF contribution'
    )
    insurance_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    loan_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    
    # Working days/hours
    working_days = models.IntegerField(default=0)
    absent_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0'))
    
    # Payment details
    payment_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['employee', 'period']
        ordering = ['-period__year', '-period__month']
    
    @property
    def gross_pay(self):
        """Calculate total gross pay"""
        return (
            self.basic_salary + 
            self.overtime_pay + 
            self.allowances + 
            self.bonus + 
            self.commission + 
            self.other_earnings
        )
    
    @property
    def total_deductions(self):
        """Calculate total deductions"""
        return (
            self.tax_deduction + 
            self.mpf_employee + 
            self.insurance_deduction + 
            self.loan_deduction + 
            self.other_deductions
        )
    
    @property
    def net_pay(self):
        """Calculate net pay"""
        return self.gross_pay - self.total_deductions
    
    def __str__(self):
        return f"{self.employee.employee_id} - {self.period.name}"


class PayrollItem(BaseModel):
    """Detailed breakdown of payroll earnings/deductions"""
    payroll = models.ForeignKey(
        Payroll,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item_type = models.CharField(
        max_length=20,
        choices=[('EARNING', 'Earning'), ('DEDUCTION', 'Deduction')],
        default='EARNING'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    def __str__(self):
        return f"{self.payroll.employee.employee_id} - {self.name}: {self.amount}"


# =================================================================
# Project Models (Keeping existing)
# =================================================================

class ProjectStatuses(str, Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class Project(BaseModel):
    """Internal HR projects"""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, 
        choices=ProjectStatuses.choices(), 
        default=ProjectStatuses.CREATED.value
    )
    owner = models.ForeignKey(
        'users.User', 
        on_delete=models.PROTECT, 
        related_name='owned_projects'
    )
    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    def __str__(self):
        return self.name


class UserProjectMapping(BaseModel):
    """Project team membership"""
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.PROTECT, 
        related_name='project_mappings'
    )
    project = models.ForeignKey(
        Project, 
        on_delete=models.PROTECT, 
        related_name='user_mappings'
    )
    role = models.CharField(max_length=50, blank=True, help_text='Role in project')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'project']


class TaskStatuses(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    DONE = "DONE"
    BLOCKED = "BLOCKED"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class Task(BaseModel):
    """Project tasks"""
    project = models.ForeignKey(
        Project, 
        on_delete=models.PROTECT, 
        related_name='tasks'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, 
        choices=TaskStatuses.choices(), 
        default=TaskStatuses.TODO.value
    )
    priority = models.CharField(
        max_length=20,
        choices=TaskPriority.choices(),
        default=TaskPriority.MEDIUM.value
    )
    assigned_to = models.ForeignKey(
        'users.User', 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks_hrms'
    )
    assigned_by = models.ForeignKey(
        'users.User', 
        on_delete=models.SET_NULL, 
        related_name='created_tasks', 
        null=True, 
        blank=True
    )
    estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0')
    )
    actual_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0')
    )

    class Meta:
        ordering = ['-priority', 'due_date']

    def __str__(self):
        return self.title

