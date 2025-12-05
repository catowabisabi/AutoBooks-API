from django.contrib import admin
from .models import (
    FiscalYear, AccountingPeriod, Currency, TaxRate, Account,
    JournalEntry, JournalEntryLine, Contact, Invoice, InvoiceLine,
    Payment, PaymentAllocation, Expense, BankStatement, BankTransaction,
    APIKeyStore
)


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_active', 'is_closed']
    list_filter = ['is_active', 'is_closed']


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'fiscal_year', 'period_number', 'start_date', 'end_date', 'is_closed']
    list_filter = ['fiscal_year', 'is_closed']


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'symbol', 'exchange_rate', 'is_base']
    list_filter = ['is_base']
    search_fields = ['code', 'name']


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ['name', 'rate', 'is_active']
    list_filter = ['is_active']


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'account_subtype', 'current_balance', 'is_active']
    list_filter = ['account_type', 'account_subtype', 'is_active']
    search_fields = ['code', 'name']
    ordering = ['code']


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 2


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['entry_number', 'date', 'description', 'total_debit', 'total_credit', 'status']
    list_filter = ['status', 'date']
    search_fields = ['entry_number', 'description']
    inlines = [JournalEntryLineInline]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['contact_name', 'company_name', 'contact_type', 'email', 'phone', 'is_active']
    list_filter = ['contact_type', 'is_active']
    search_fields = ['contact_name', 'company_name', 'email']


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'invoice_type', 'contact', 'issue_date', 'total', 'amount_due', 'status']
    list_filter = ['invoice_type', 'status', 'issue_date']
    search_fields = ['invoice_number', 'contact__contact_name']
    inlines = [InvoiceLineInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_number', 'payment_type', 'contact', 'date', 'amount', 'payment_method', 'status']
    list_filter = ['payment_type', 'payment_method', 'status', 'date']
    search_fields = ['payment_number', 'contact__contact_name']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['expense_number', 'employee', 'date', 'category', 'amount', 'status', 'is_reimbursed']
    list_filter = ['status', 'is_reimbursed', 'date']
    search_fields = ['expense_number', 'description']


@admin.register(BankStatement)
class BankStatementAdmin(admin.ModelAdmin):
    list_display = ['bank_account', 'statement_date', 'opening_balance', 'closing_balance', 'is_reconciled']
    list_filter = ['is_reconciled', 'statement_date']


@admin.register(APIKeyStore)
class APIKeyStoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'is_active', 'usage_count', 'last_used_at']
    list_filter = ['provider', 'is_active']
    search_fields = ['name']
