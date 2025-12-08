"""
Accounting Module Models
========================
Complete double-entry bookkeeping system for ERP with multi-tenant support.
"""

from enum import Enum
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.models import BaseModel
from core.tenants.managers import TenantAwareManager, UnscopedManager


# =================================================================
# Enums
# =================================================================

class AccountType(str, Enum):
    """Types of accounts in Chart of Accounts"""
    ASSET = 'ASSET'                    # 資產
    LIABILITY = 'LIABILITY'            # 負債
    EQUITY = 'EQUITY'                  # 權益
    REVENUE = 'REVENUE'                # 收入
    EXPENSE = 'EXPENSE'                # 費用
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class AccountSubType(str, Enum):
    """Subtypes for more detailed classification"""
    # Asset subtypes
    CASH = 'CASH'                      # 現金
    BANK = 'BANK'                      # 銀行
    ACCOUNTS_RECEIVABLE = 'ACCOUNTS_RECEIVABLE'  # 應收帳款
    INVENTORY = 'INVENTORY'            # 存貨
    FIXED_ASSET = 'FIXED_ASSET'        # 固定資產
    OTHER_ASSET = 'OTHER_ASSET'        # 其他資產
    
    # Liability subtypes
    ACCOUNTS_PAYABLE = 'ACCOUNTS_PAYABLE'  # 應付帳款
    CREDIT_CARD = 'CREDIT_CARD'        # 信用卡
    TAX_PAYABLE = 'TAX_PAYABLE'        # 應付稅款
    LOAN = 'LOAN'                      # 貸款
    OTHER_LIABILITY = 'OTHER_LIABILITY'  # 其他負債
    
    # Equity subtypes
    RETAINED_EARNINGS = 'RETAINED_EARNINGS'  # 保留盈餘
    SHARE_CAPITAL = 'SHARE_CAPITAL'    # 股本
    
    # Revenue subtypes
    SALES = 'SALES'                    # 銷售收入
    SERVICE = 'SERVICE'                # 服務收入
    OTHER_INCOME = 'OTHER_INCOME'      # 其他收入
    
    # Expense subtypes
    COST_OF_GOODS = 'COST_OF_GOODS'    # 銷貨成本
    OPERATING = 'OPERATING'            # 營業費用
    PAYROLL = 'PAYROLL'                # 薪資費用
    RENT = 'RENT'                      # 租金
    UTILITIES = 'UTILITIES'            # 水電費
    OTHER_EXPENSE = 'OTHER_EXPENSE'    # 其他費用
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class TransactionStatus(str, Enum):
    """Status of financial transactions"""
    DRAFT = 'DRAFT'
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    POSTED = 'POSTED'
    VOIDED = 'VOIDED'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class InvoiceStatus(str, Enum):
    """Invoice status"""
    DRAFT = 'DRAFT'
    SENT = 'SENT'
    VIEWED = 'VIEWED'
    PARTIAL = 'PARTIAL'
    PAID = 'PAID'
    OVERDUE = 'OVERDUE'
    CANCELLED = 'CANCELLED'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class PaymentMethod(str, Enum):
    """Payment methods"""
    CASH = 'CASH'
    BANK_TRANSFER = 'BANK_TRANSFER'
    CREDIT_CARD = 'CREDIT_CARD'
    DEBIT_CARD = 'DEBIT_CARD'
    CHECK = 'CHECK'
    PAYPAL = 'PAYPAL'
    OTHER = 'OTHER'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


# =================================================================
# Core Accounting Models
# =================================================================

class FiscalYear(BaseModel):
    """會計年度"""
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='fiscal_years',
        null=True,  # Temporarily nullable for migration
        blank=True
    )
    name = models.CharField(max_length=100)  # e.g., "FY 2024"
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    is_closed = models.BooleanField(default=False)
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Fiscal Year'
        verbose_name_plural = 'Fiscal Years'
    
    def __str__(self):
        return self.name


class AccountingPeriod(BaseModel):
    """會計期間 (月/季)"""
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='accounting_periods',
        null=True,
        blank=True
    )
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='periods')
    name = models.CharField(max_length=100)  # e.g., "January 2024"
    period_number = models.PositiveIntegerField()  # 1-12 for months
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        ordering = ['fiscal_year', 'period_number']
        unique_together = ['fiscal_year', 'period_number']
    
    def __str__(self):
        return f"{self.fiscal_year.name} - {self.name}"


class Currency(BaseModel):
    """貨幣"""
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='currencies',
        null=True,
        blank=True
    )
    code = models.CharField(max_length=3)  # ISO 4217
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, default=Decimal('1.000000'))
    is_base = models.BooleanField(default=False)
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        verbose_name_plural = 'Currencies'
        unique_together = ['tenant', 'code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class TaxRate(BaseModel):
    """稅率"""
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='tax_rates',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)  # e.g., "GST 5%"
    rate = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class Account(BaseModel):
    """會計科目表 (Chart of Accounts)"""
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='accounts',
        null=True,
        blank=True
    )
    code = models.CharField(max_length=20)  # e.g., "1000", "1100"
    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=20, choices=AccountType.choices())
    account_subtype = models.CharField(max_length=30, choices=AccountSubType.choices(), blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    description = models.TextField(blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)  # System accounts cannot be deleted
    
    # Balance tracking
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        ordering = ['code']
        unique_together = ['tenant', 'code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def is_debit_positive(self):
        """Assets and Expenses increase with debits"""
        return self.account_type in [AccountType.ASSET.value, AccountType.EXPENSE.value]


# =================================================================
# Journal Entry Models
# =================================================================

class JournalEntry(BaseModel):
    """日記帳分錄"""
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='journal_entries',
        null=True,
        blank=True
    )
    entry_number = models.CharField(max_length=50)  # unique per tenant
    date = models.DateField()
    description = models.TextField()
    reference = models.CharField(max_length=100, blank=True)  # External reference
    
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT, null=True)
    period = models.ForeignKey(AccountingPeriod, on_delete=models.PROTECT, null=True)
    
    # Link to project
    project = models.ForeignKey(
        'Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='journal_entries'
    )
    
    status = models.CharField(max_length=20, choices=TransactionStatus.choices(), default=TransactionStatus.DRAFT.value)
    
    # Audit trail
    created_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='journal_entries_created')
    approved_by = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True, related_name='journal_entries_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    
    # Totals (for quick reference)
    total_debit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_credit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name_plural = 'Journal Entries'
        unique_together = ['tenant', 'entry_number']
    
    def __str__(self):
        return f"{self.entry_number} - {self.date}"
    
    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit


class JournalEntryLine(BaseModel):
    """日記帳分錄明細"""
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='journal_lines')
    description = models.CharField(max_length=500, blank=True)
    
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # For multi-currency support
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, default=Decimal('1.000000'))
    foreign_debit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    foreign_credit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.account.code}: Dr {self.debit} / Cr {self.credit}"


# =================================================================
# Customer & Vendor Models
# =================================================================

class Contact(BaseModel):
    """客戶/供應商聯絡人"""
    CONTACT_TYPE_CHOICES = [
        ('CUSTOMER', 'Customer'),
        ('VENDOR', 'Vendor'),
        ('BOTH', 'Both'),
    ]
    
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='contacts',
        null=True,
        blank=True
    )
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPE_CHOICES)
    company_name = models.CharField(max_length=200, blank=True)
    contact_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    
    # Address
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Financial
    tax_number = models.CharField(max_length=50, blank=True)  # VAT/GST number
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)
    payment_terms = models.PositiveIntegerField(default=30)  # Days
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Linked accounts
    receivable_account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name='customer_contacts')
    payable_account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name='vendor_contacts')
    
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    def __str__(self):
        return self.company_name or self.contact_name


# =================================================================
# Invoice Models
# =================================================================

class Invoice(BaseModel):
    """發票 (銷售發票/採購發票)"""
    INVOICE_TYPE_CHOICES = [
        ('SALES', 'Sales Invoice'),      # 銷售發票
        ('PURCHASE', 'Purchase Invoice'),  # 採購發票
    ]
    
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='invoices',
        null=True,
        blank=True
    )
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPE_CHOICES)
    invoice_number = models.CharField(max_length=50)  # unique per tenant
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name='invoices')
    
    # Link to project
    project = models.ForeignKey(
        'Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )
    
    issue_date = models.DateField()
    due_date = models.DateField()
    
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices(), default=InvoiceStatus.DRAFT.value)
    
    # Currency
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, default=Decimal('1.000000'))
    
    # Amounts
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    amount_due = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Additional info
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    
    # Linked journal entry
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    
    # Audit
    created_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='invoices_created')
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        ordering = ['-issue_date', '-created_at']
        unique_together = ['tenant', 'invoice_number']
    
    def __str__(self):
        return f"{self.invoice_number} - {self.contact}"


class InvoiceLine(BaseModel):
    """發票明細"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(max_length=500)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    
    quantity = models.DecimalField(max_digits=15, decimal_places=4, default=Decimal('1'))
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Tax
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.PROTECT, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Discount
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Total
    line_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.description} x {self.quantity}"


# =================================================================
# Payment Models
# =================================================================

class Payment(BaseModel):
    """付款/收款記錄"""
    PAYMENT_TYPE_CHOICES = [
        ('RECEIVE', 'Payment Received'),   # 收款
        ('MAKE', 'Payment Made'),          # 付款
    ]
    
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    payment_number = models.CharField(max_length=50)  # unique per tenant
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name='payments')
    
    date = models.DateField()
    
    # Payment details
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices())
    payment_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='payments')  # Bank/Cash account
    
    # Currency
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, default=Decimal('1.000000'))
    
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=TransactionStatus.choices(), default=TransactionStatus.DRAFT.value)
    
    # Linked journal entry
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    
    # Audit
    created_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='payments_created')
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        ordering = ['-date', '-created_at']
        unique_together = ['tenant', 'payment_number']
    
    def __str__(self):
        return f"{self.payment_number} - {self.amount}"


class PaymentAllocation(BaseModel):
    """付款分配到發票"""
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='allocations')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payment_allocations')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    class Meta:
        unique_together = ['payment', 'invoice']


# =================================================================
# Expense Models
# =================================================================

class Expense(BaseModel):
    """費用報銷"""
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='expenses',
        null=True,
        blank=True
    )
    expense_number = models.CharField(max_length=50)  # unique per tenant
    employee = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='expenses')
    
    # Link to project
    project = models.ForeignKey(
        'Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )
    
    date = models.DateField()
    category = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='expenses')  # Expense account
    
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Currency
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, default=Decimal('1.000000'))
    
    # Tax
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.PROTECT, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Approval
    status = models.CharField(max_length=20, choices=TransactionStatus.choices(), default=TransactionStatus.PENDING.value)
    approved_by = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True, related_name='expenses_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Receipt
    receipt_image = models.ImageField(upload_to='receipts/', null=True, blank=True)
    receipt_data = models.JSONField(null=True, blank=True)  # OCR extracted data
    
    # Linked journal entry
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    
    # Reimbursement
    is_reimbursed = models.BooleanField(default=False)
    reimbursed_at = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        ordering = ['-date', '-created_at']
        unique_together = ['tenant', 'expense_number']
    
    def __str__(self):
        return f"{self.expense_number} - {self.description[:50]}"


# =================================================================
# Bank Reconciliation
# =================================================================

class BankStatement(BaseModel):
    """銀行對帳單"""
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='bank_statements',
        null=True,
        blank=True
    )
    bank_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='bank_statements')
    statement_date = models.DateField()
    
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2)
    
    is_reconciled = models.BooleanField(default=False)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    reconciled_by = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True)
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        ordering = ['-statement_date']
        unique_together = ['tenant', 'bank_account', 'statement_date']


class BankTransaction(BaseModel):
    """銀行交易"""
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='bank_transactions',
        null=True,
        blank=True
    )
    statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateField()
    description = models.CharField(max_length=500)
    reference = models.CharField(max_length=100, blank=True)
    
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    is_matched = models.BooleanField(default=False)
    matched_journal_line = models.ForeignKey(JournalEntryLine, on_delete=models.SET_NULL, null=True, blank=True)
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        ordering = ['date']


# =================================================================
# API Key Storage Model
# =================================================================

class APIKeyStore(BaseModel):
    """API Key 安全存儲"""
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='api_keys',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)  # e.g., "OPENAI_API_KEY" - unique per tenant
    encrypted_value = models.TextField()  # Encrypted API key
    provider = models.CharField(max_length=50)  # e.g., "openai", "google", "deepseek"
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    
    created_by = models.ForeignKey('users.User', on_delete=models.PROTECT)
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
        unique_together = ['tenant', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.provider})"


# =================================================================
# Receipt Management with Recognition Status
# =================================================================

class RecognitionStatus(str, Enum):
    """Receipt recognition status"""
    PENDING = 'PENDING'          # Awaiting processing
    RECOGNIZED = 'RECOGNIZED'    # Successfully extracted data
    UNRECOGNIZED = 'UNRECOGNIZED'  # Failed to extract/low confidence
    MANUALLY_CLASSIFIED = 'MANUALLY_CLASSIFIED'  # Manually categorized
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class Receipt(BaseModel):
    """收據文件 - Receipt with recognition status for bulk upload"""
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='receipts',
        null=True,
        blank=True
    )
    
    # File Information
    file = models.FileField(upload_to='receipts/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)  # in bytes
    mime_type = models.CharField(max_length=100, blank=True)
    
    # Recognition Status
    recognition_status = models.CharField(
        max_length=30,
        choices=RecognitionStatus.choices(),
        default=RecognitionStatus.PENDING.value
    )
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.0000'))]
    )
    confidence_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.7000'),
        help_text='Minimum confidence for automatic recognition'
    )
    
    # Extracted Data (OCR/AI results)
    extracted_data = models.JSONField(null=True, blank=True)  # Raw OCR result
    vendor_name = models.CharField(max_length=255, blank=True)
    receipt_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    currency_code = models.CharField(max_length=3, blank=True, default='TWD')
    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    description = models.TextField(blank=True)
    
    # Manual Classification Data
    manual_category = models.ForeignKey(
        'Account',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='categorized_receipts',
        help_text='Manually assigned expense category'
    )
    manual_vendor = models.CharField(max_length=255, blank=True)
    manual_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    manual_date = models.DateField(null=True, blank=True)
    classification_notes = models.TextField(blank=True)
    classified_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classified_receipts'
    )
    classified_at = models.DateTimeField(null=True, blank=True)
    
    # Linked documents
    project = models.ForeignKey(
        'Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipts'
    )
    expense = models.ForeignKey(
        'Expense',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_receipts'
    )
    
    # Processing metadata
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    
    # Upload metadata
    uploaded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='uploaded_receipts'
    )
    batch_id = models.UUIDField(null=True, blank=True, db_index=True)  # For grouping bulk uploads
    
    # Tags for organization
    tags = models.JSONField(default=list, blank=True)
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Receipt'
        verbose_name_plural = 'Receipts'
        indexes = [
            models.Index(fields=['recognition_status', 'created_at']),
            models.Index(fields=['batch_id']),
            models.Index(fields=['tenant', 'recognition_status']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} ({self.recognition_status})"
    
    @property
    def is_recognized(self):
        return self.recognition_status == RecognitionStatus.RECOGNIZED.value
    
    @property
    def needs_manual_review(self):
        return self.recognition_status == RecognitionStatus.UNRECOGNIZED.value
    
    @property
    def final_amount(self):
        """Get the final amount (manual overrides extracted)"""
        return self.manual_amount or self.total_amount
    
    @property
    def final_vendor(self):
        """Get the final vendor (manual overrides extracted)"""
        return self.manual_vendor or self.vendor_name
    
    @property
    def final_date(self):
        """Get the final date (manual overrides extracted)"""
        return self.manual_date or self.receipt_date


# =================================================================
# Extracted Field with Bounding Box
# =================================================================

class ExtractedFieldType(str, Enum):
    """Types of fields that can be extracted from receipts"""
    VENDOR = 'VENDOR'
    TOTAL = 'TOTAL'
    DATE = 'DATE'
    CURRENCY = 'CURRENCY'
    TAX = 'TAX'
    CATEGORY = 'CATEGORY'
    SUBTOTAL = 'SUBTOTAL'
    TIP = 'TIP'
    PAYMENT_METHOD = 'PAYMENT_METHOD'
    INVOICE_NUMBER = 'INVOICE_NUMBER'
    LINE_ITEM = 'LINE_ITEM'
    OTHER = 'OTHER'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class ExtractedField(BaseModel):
    """
    Stores individual extracted fields from receipts with bounding boxes.
    Each field has coordinates for UI highlighting and confidence scores.
    """
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name='extracted_fields'
    )
    
    # Field identification
    field_type = models.CharField(
        max_length=30,
        choices=ExtractedFieldType.choices()
    )
    field_name = models.CharField(max_length=100)  # e.g., "vendor_name", "total_amount"
    
    # Extracted value
    raw_value = models.TextField(blank=True)  # Original OCR text
    normalized_value = models.TextField(blank=True)  # Cleaned/parsed value
    data_type = models.CharField(
        max_length=20, 
        default='string',
        help_text='string, number, date, currency'
    )
    
    # Bounding box coordinates (relative to image, 0-1 scale or pixels)
    bbox_x1 = models.FloatField(null=True, blank=True, help_text='Left coordinate')
    bbox_y1 = models.FloatField(null=True, blank=True, help_text='Top coordinate')
    bbox_x2 = models.FloatField(null=True, blank=True, help_text='Right coordinate')
    bbox_y2 = models.FloatField(null=True, blank=True, help_text='Bottom coordinate')
    bbox_unit = models.CharField(
        max_length=10,
        default='ratio',
        help_text='ratio (0-1) or pixel'
    )
    page_number = models.PositiveSmallIntegerField(default=1, help_text='Page number for multi-page receipts')
    
    # Confidence score for this specific field
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.0000'))]
    )
    
    # Override values (from manual correction)
    is_corrected = models.BooleanField(default=False)
    corrected_value = models.TextField(blank=True)
    corrected_bbox_x1 = models.FloatField(null=True, blank=True)
    corrected_bbox_y1 = models.FloatField(null=True, blank=True)
    corrected_bbox_x2 = models.FloatField(null=True, blank=True)
    corrected_bbox_y2 = models.FloatField(null=True, blank=True)
    corrected_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='corrected_fields'
    )
    corrected_at = models.DateTimeField(null=True, blank=True)
    
    # Version tracking
    version = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['field_type', 'created_at']
        indexes = [
            models.Index(fields=['receipt', 'field_type']),
            models.Index(fields=['is_corrected']),
        ]
    
    def __str__(self):
        return f"{self.receipt.original_filename} - {self.field_type}: {self.final_value[:50] if self.final_value else 'N/A'}"
    
    @property
    def final_value(self):
        """Get the final value (corrected overrides extracted)"""
        return self.corrected_value if self.is_corrected else self.normalized_value or self.raw_value
    
    @property
    def final_bbox(self):
        """Get the final bounding box (corrected overrides extracted)"""
        if self.is_corrected and self.corrected_bbox_x1 is not None:
            return {
                'x1': self.corrected_bbox_x1,
                'y1': self.corrected_bbox_y1,
                'x2': self.corrected_bbox_x2,
                'y2': self.corrected_bbox_y2,
            }
        return {
            'x1': self.bbox_x1,
            'y1': self.bbox_y1,
            'x2': self.bbox_x2,
            'y2': self.bbox_y2,
        }
    
    @property
    def has_bbox(self):
        """Check if bounding box coordinates exist"""
        return all(v is not None for v in [self.bbox_x1, self.bbox_y1, self.bbox_x2, self.bbox_y2])


class FieldCorrectionHistory(BaseModel):
    """
    Audit trail for field corrections.
    Stores previous values whenever a field is corrected for version history.
    """
    extracted_field = models.ForeignKey(
        ExtractedField,
        on_delete=models.CASCADE,
        related_name='correction_history'
    )
    
    # Version info
    version = models.PositiveIntegerField()
    
    # Previous values before correction
    previous_value = models.TextField(blank=True)
    previous_bbox_x1 = models.FloatField(null=True, blank=True)
    previous_bbox_y1 = models.FloatField(null=True, blank=True)
    previous_bbox_x2 = models.FloatField(null=True, blank=True)
    previous_bbox_y2 = models.FloatField(null=True, blank=True)
    
    # New values after correction
    new_value = models.TextField(blank=True)
    new_bbox_x1 = models.FloatField(null=True, blank=True)
    new_bbox_y1 = models.FloatField(null=True, blank=True)
    new_bbox_x2 = models.FloatField(null=True, blank=True)
    new_bbox_y2 = models.FloatField(null=True, blank=True)
    
    # Correction metadata
    correction_reason = models.TextField(blank=True)
    corrected_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='field_corrections'
    )
    corrected_at = models.DateTimeField(auto_now_add=True)
    
    # Source of correction
    correction_source = models.CharField(
        max_length=30,
        default='MANUAL',
        help_text='MANUAL, AI_SUGGESTION, BATCH_UPDATE'
    )
    
    class Meta:
        ordering = ['-corrected_at']
        verbose_name = 'Field Correction History'
        verbose_name_plural = 'Field Correction Histories'
        indexes = [
            models.Index(fields=['extracted_field', 'version']),
            models.Index(fields=['corrected_by', 'corrected_at']),
        ]
    
    def __str__(self):
        return f"{self.extracted_field.field_type} v{self.version} - {self.corrected_at}"


class ReceiptCorrectionSummary(BaseModel):
    """
    Summary of all corrections made to a receipt.
    Provides quick access to correction statistics and overall audit trail.
    """
    receipt = models.OneToOneField(
        Receipt,
        on_delete=models.CASCADE,
        related_name='correction_summary'
    )
    
    # Correction statistics
    total_fields = models.PositiveIntegerField(default=0)
    corrected_fields = models.PositiveIntegerField(default=0)
    total_corrections = models.PositiveIntegerField(default=0)  # Including multiple corrections per field
    
    # First and last correction
    first_corrected_at = models.DateTimeField(null=True, blank=True)
    last_corrected_at = models.DateTimeField(null=True, blank=True)
    
    # Users involved
    corrected_by_users = models.JSONField(default=list, blank=True)  # List of user IDs
    
    # Overall confidence improvement
    original_avg_confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Receipt Correction Summary'
        verbose_name_plural = 'Receipt Correction Summaries'
    
    def __str__(self):
        return f"{self.receipt.original_filename} - {self.corrected_fields}/{self.total_fields} corrected"
    
    def update_statistics(self):
        """Update correction statistics based on current field data"""
        fields = self.receipt.extracted_fields.all()
        self.total_fields = fields.count()
        self.corrected_fields = fields.filter(is_corrected=True).count()
        
        # Count total correction history entries
        from django.db.models import Count
        self.total_corrections = FieldCorrectionHistory.objects.filter(
            extracted_field__receipt=self.receipt
        ).count()
        
        # Get first and last correction times
        history = FieldCorrectionHistory.objects.filter(
            extracted_field__receipt=self.receipt
        ).order_by('corrected_at')
        
        if history.exists():
            self.first_corrected_at = history.first().corrected_at
            self.last_corrected_at = history.last().corrected_at
            
            # Get unique correctors
            corrector_ids = list(history.values_list('corrected_by_id', flat=True).distinct())
            self.corrected_by_users = [str(uid) for uid in corrector_ids if uid]
        
        # Calculate original average confidence
        from django.db.models import Avg
        avg_conf = fields.aggregate(avg=Avg('confidence_score'))['avg']
        self.original_avg_confidence = avg_conf
        
        self.save()


# =================================================================
# Project Management for Accounting
# =================================================================

class ProjectStatus(str, Enum):
    """Project status"""
    ACTIVE = 'ACTIVE'
    COMPLETED = 'COMPLETED'
    ON_HOLD = 'ON_HOLD'
    CANCELLED = 'CANCELLED'
    ARCHIVED = 'ARCHIVED'
    
    @classmethod
    def choices(cls):
        return [(tag.value, tag.value) for tag in cls]


class Project(BaseModel):
    """會計專案 - Links accounting documents together"""
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='accounting_projects',
        null=True,
        blank=True
    )
    
    # Basic Info
    code = models.CharField(max_length=50)  # Unique per tenant, e.g., "PROJ-2024-001"
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Status & Dates
    status = models.CharField(
        max_length=20, 
        choices=ProjectStatus.choices(), 
        default=ProjectStatus.ACTIVE.value
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Budget Tracking
    budget_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.ForeignKey(
        Currency, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='projects'
    )
    
    # Client/Contact (optional)
    client = models.ForeignKey(
        'Contact', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='projects'
    )
    
    # Categorization
    category = models.CharField(max_length=100, blank=True)  # e.g., "Audit", "Tax", "Consulting"
    tags = models.JSONField(default=list, blank=True)  # ["urgent", "annual", "2024"]
    
    # Ownership
    created_by = models.ForeignKey(
        'users.User', 
        on_delete=models.PROTECT, 
        related_name='created_projects'
    )
    manager = models.ForeignKey(
        'users.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='managed_projects'
    )
    
    # Notes & Settings
    notes = models.TextField(blank=True)
    settings = models.JSONField(default=dict, blank=True)
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['tenant', 'code']
        verbose_name = 'Accounting Project'
        verbose_name_plural = 'Accounting Projects'
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def total_expenses(self):
        """Calculate total expenses linked to this project"""
        return self.expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    @property
    def total_invoiced(self):
        """Calculate total invoiced amount for this project"""
        return self.invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    @property
    def budget_remaining(self):
        """Calculate remaining budget"""
        return self.budget_amount - self.total_expenses
    
    @property
    def budget_utilization_percent(self):
        """Calculate budget utilization percentage"""
        if self.budget_amount > 0:
            return (self.total_expenses / self.budget_amount * 100).quantize(Decimal('0.01'))
        return Decimal('0.00')


class ProjectDocument(BaseModel):
    """Link documents/files to projects"""
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='project_documents',
        null=True,
        blank=True
    )
    
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='documents'
    )
    
    # Document Info
    document_type = models.CharField(max_length=50)  # 'receipt', 'contract', 'report', 'other'
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # File Storage
    file = models.FileField(upload_to='project_documents/', null=True, blank=True)
    file_url = models.URLField(blank=True)  # External URL if not uploaded
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(default=0)  # in bytes
    mime_type = models.CharField(max_length=100, blank=True)
    
    # Metadata
    uploaded_by = models.ForeignKey(
        'users.User', 
        on_delete=models.PROTECT,
        related_name='uploaded_project_documents'
    )
    tags = models.JSONField(default=list, blank=True)
    
    objects = TenantAwareManager()
    all_objects = UnscopedManager()
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.project.code} - {self.title}"
