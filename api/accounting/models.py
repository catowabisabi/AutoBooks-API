"""
Accounting Module Models
========================
Complete double-entry bookkeeping system for ERP.
"""

from enum import Enum
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.models import BaseModel


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
    name = models.CharField(max_length=100)  # e.g., "FY 2024"
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    is_closed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Fiscal Year'
        verbose_name_plural = 'Fiscal Years'
    
    def __str__(self):
        return self.name


class AccountingPeriod(BaseModel):
    """會計期間 (月/季)"""
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='periods')
    name = models.CharField(max_length=100)  # e.g., "January 2024"
    period_number = models.PositiveIntegerField()  # 1-12 for months
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['fiscal_year', 'period_number']
        unique_together = ['fiscal_year', 'period_number']
    
    def __str__(self):
        return f"{self.fiscal_year.name} - {self.name}"


class Currency(BaseModel):
    """貨幣"""
    code = models.CharField(max_length=3, unique=True)  # ISO 4217
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, default=Decimal('1.000000'))
    is_base = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = 'Currencies'
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class TaxRate(BaseModel):
    """稅率"""
    name = models.CharField(max_length=100)  # e.g., "GST 5%"
    rate = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class Account(BaseModel):
    """會計科目表 (Chart of Accounts)"""
    code = models.CharField(max_length=20, unique=True)  # e.g., "1000", "1100"
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
    
    class Meta:
        ordering = ['code']
    
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
    entry_number = models.CharField(max_length=50, unique=True)
    date = models.DateField()
    description = models.TextField()
    reference = models.CharField(max_length=100, blank=True)  # External reference
    
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT, null=True)
    period = models.ForeignKey(AccountingPeriod, on_delete=models.PROTECT, null=True)
    
    status = models.CharField(max_length=20, choices=TransactionStatus.choices(), default=TransactionStatus.DRAFT.value)
    
    # Audit trail
    created_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='journal_entries_created')
    approved_by = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True, related_name='journal_entries_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    
    # Totals (for quick reference)
    total_debit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_credit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name_plural = 'Journal Entries'
    
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
    
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPE_CHOICES)
    invoice_number = models.CharField(max_length=50, unique=True)
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name='invoices')
    
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
    
    class Meta:
        ordering = ['-issue_date', '-created_at']
    
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
    
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    payment_number = models.CharField(max_length=50, unique=True)
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
    
    class Meta:
        ordering = ['-date', '-created_at']
    
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
    expense_number = models.CharField(max_length=50, unique=True)
    employee = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='expenses')
    
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
    
    class Meta:
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.expense_number} - {self.description[:50]}"


# =================================================================
# Bank Reconciliation
# =================================================================

class BankStatement(BaseModel):
    """銀行對帳單"""
    bank_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='bank_statements')
    statement_date = models.DateField()
    
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2)
    
    is_reconciled = models.BooleanField(default=False)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    reconciled_by = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True)
    
    class Meta:
        ordering = ['-statement_date']
        unique_together = ['bank_account', 'statement_date']


class BankTransaction(BaseModel):
    """銀行交易"""
    statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateField()
    description = models.CharField(max_length=500)
    reference = models.CharField(max_length=100, blank=True)
    
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    is_matched = models.BooleanField(default=False)
    matched_journal_line = models.ForeignKey(JournalEntryLine, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['date']


# =================================================================
# API Key Storage Model
# =================================================================

class APIKeyStore(BaseModel):
    """API Key 安全存儲"""
    name = models.CharField(max_length=100, unique=True)  # e.g., "OPENAI_API_KEY"
    encrypted_value = models.TextField()  # Encrypted API key
    provider = models.CharField(max_length=50)  # e.g., "openai", "google", "deepseek"
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    
    created_by = models.ForeignKey('users.User', on_delete=models.PROTECT)
    
    class Meta:
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
    
    def __str__(self):
        return f"{self.name} ({self.provider})"
