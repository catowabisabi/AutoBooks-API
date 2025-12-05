from rest_framework import serializers
from .models import (
    FiscalYear, AccountingPeriod, Currency, TaxRate, Account,
    JournalEntry, JournalEntryLine, Contact, Invoice, InvoiceLine,
    Payment, PaymentAllocation, Expense
)


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = '__all__'


class TaxRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRate
        fields = '__all__'


class FiscalYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiscalYear
        fields = '__all__'


class AccountingPeriodSerializer(serializers.ModelSerializer):
    fiscal_year_name = serializers.CharField(source='fiscal_year.name', read_only=True)
    
    class Meta:
        model = AccountingPeriod
        fields = '__all__'


class AccountSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    
    class Meta:
        model = Account
        fields = '__all__'


class AccountListSerializer(serializers.ModelSerializer):
    """Simplified serializer for dropdowns and lists"""
    class Meta:
        model = Account
        fields = ['id', 'code', 'name', 'account_type', 'account_subtype', 'current_balance']


class JournalEntryLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    
    class Meta:
        model = JournalEntryLine
        fields = '__all__'


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalEntryLineSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    is_balanced = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = JournalEntry
        fields = '__all__'


class JournalEntryCreateSerializer(serializers.ModelSerializer):
    lines = JournalEntryLineSerializer(many=True)
    
    class Meta:
        model = JournalEntry
        fields = ['date', 'description', 'reference', 'lines']
    
    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        
        # Generate entry number
        from django.utils import timezone
        import uuid
        entry_number = f"JE-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        journal_entry = JournalEntry.objects.create(
            entry_number=entry_number,
            **validated_data
        )
        
        total_debit = 0
        total_credit = 0
        
        for line_data in lines_data:
            JournalEntryLine.objects.create(journal_entry=journal_entry, **line_data)
            total_debit += line_data.get('debit', 0)
            total_credit += line_data.get('credit', 0)
        
        journal_entry.total_debit = total_debit
        journal_entry.total_credit = total_credit
        journal_entry.save()
        
        return journal_entry


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'


class ContactListSerializer(serializers.ModelSerializer):
    """Simplified serializer for dropdowns"""
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Contact
        fields = ['id', 'display_name', 'contact_type', 'email', 'phone']
    
    def get_display_name(self, obj):
        return obj.company_name or obj.contact_name


class InvoiceLineSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    tax_rate_name = serializers.CharField(source='tax_rate.name', read_only=True)
    
    class Meta:
        model = InvoiceLine
        fields = '__all__'


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)
    contact_name = serializers.SerializerMethodField()
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    
    class Meta:
        model = Invoice
        fields = '__all__'
    
    def get_contact_name(self, obj):
        return obj.contact.company_name or obj.contact.contact_name


class InvoiceListSerializer(serializers.ModelSerializer):
    """Simplified serializer for lists"""
    contact_name = serializers.SerializerMethodField()
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    
    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'invoice_type', 'contact_name', 
                  'issue_date', 'due_date', 'total', 'amount_due', 'status', 'currency_code']
    
    def get_contact_name(self, obj):
        return obj.contact.company_name or obj.contact.contact_name


class PaymentSerializer(serializers.ModelSerializer):
    contact_name = serializers.SerializerMethodField()
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    
    class Meta:
        model = Payment
        fields = '__all__'
    
    def get_contact_name(self, obj):
        return obj.contact.company_name or obj.contact.contact_name


class PaymentAllocationSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    
    class Meta:
        model = PaymentAllocation
        fields = '__all__'


class ExpenseSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    
    class Meta:
        model = Expense
        fields = '__all__'


class ExpenseListSerializer(serializers.ModelSerializer):
    """Simplified serializer for lists"""
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Expense
        fields = ['id', 'expense_number', 'employee_name', 'date', 
                  'category_name', 'amount', 'status', 'is_reimbursed']
