from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import (
    FiscalYear, AccountingPeriod, Currency, TaxRate, Account,
    JournalEntry, JournalEntryLine, Contact, Invoice, InvoiceLine,
    Payment, PaymentAllocation, Expense, Project, ProjectDocument,
    ProjectStatus
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


# =================================================================
# Project Serializers
# =================================================================

class ProjectDocumentSerializer(serializers.ModelSerializer):
    """Serializer for project documents"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    file_size_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectDocument
        fields = [
            'id', 'project', 'document_type', 'title', 'description',
            'file', 'file_url', 'file_name', 'file_size', 'file_size_display',
            'mime_type', 'uploaded_by', 'uploaded_by_name', 'tags',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'uploaded_by']
    
    def get_file_size_display(self, obj):
        """Return human-readable file size"""
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        else:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"
    
    def validate_document_type(self, value):
        valid_types = ['receipt', 'contract', 'report', 'invoice', 'other']
        if value.lower() not in valid_types:
            raise serializers.ValidationError(
                _("Invalid document type. Must be one of: %(types)s") % {'types': ', '.join(valid_types)}
            )
        return value.lower()


class ProjectSerializer(serializers.ModelSerializer):
    """Full Project serializer with all details"""
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    manager_name = serializers.CharField(source='manager.full_name', read_only=True)
    client_name = serializers.SerializerMethodField()
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    
    # Computed fields
    total_expenses = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_invoiced = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    budget_remaining = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    budget_utilization_percent = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    # Related counts
    expense_count = serializers.SerializerMethodField()
    invoice_count = serializers.SerializerMethodField()
    journal_entry_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    
    # Nested documents (optional)
    documents = ProjectDocumentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'code', 'name', 'description', 'status',
            'start_date', 'end_date', 'budget_amount', 'currency', 'currency_code',
            'client', 'client_name', 'category', 'tags',
            'created_by', 'created_by_name', 'manager', 'manager_name',
            'notes', 'settings',
            'total_expenses', 'total_invoiced', 'budget_remaining', 'budget_utilization_percent',
            'expense_count', 'invoice_count', 'journal_entry_count', 'document_count',
            'documents',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_client_name(self, obj):
        if obj.client:
            return obj.client.company_name or obj.client.contact_name
        return None
    
    def get_expense_count(self, obj):
        return obj.expenses.count()
    
    def get_invoice_count(self, obj):
        return obj.invoices.count()
    
    def get_journal_entry_count(self, obj):
        return obj.journal_entries.count()
    
    def get_document_count(self, obj):
        return obj.documents.count()
    
    def validate_code(self, value):
        """Ensure code is unique within tenant"""
        if not value:
            raise serializers.ValidationError(_("Project code is required."))
        
        # Check uniqueness (excluding current instance on update)
        queryset = Project.objects.filter(code=value)
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            raise serializers.ValidationError(
                _("A project with code '%(code)s' already exists.") % {'code': value}
            )
        return value
    
    def validate_name(self, value):
        """Validate project name"""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError(_("Project name must be at least 2 characters."))
        if len(value) > 200:
            raise serializers.ValidationError(_("Project name cannot exceed 200 characters."))
        return value.strip()
    
    def validate_budget_amount(self, value):
        """Ensure budget is non-negative"""
        if value < 0:
            raise serializers.ValidationError(_("Budget amount cannot be negative."))
        return value
    
    def validate_status(self, value):
        """Validate status transitions"""
        valid_statuses = [s.value for s in ProjectStatus]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                _("Invalid status. Must be one of: %(statuses)s") % {'statuses': ', '.join(valid_statuses)}
            )
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        start_date = data.get('start_date') or (self.instance.start_date if self.instance else None)
        end_date = data.get('end_date') or (self.instance.end_date if self.instance else None)
        
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': _("End date cannot be before start date.")
            })
        
        return data


class ProjectListSerializer(serializers.ModelSerializer):
    """Simplified serializer for project lists"""
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    manager_name = serializers.CharField(source='manager.full_name', read_only=True)
    client_name = serializers.SerializerMethodField()
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    total_expenses = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    budget_utilization_percent = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'code', 'name', 'status', 'category',
            'start_date', 'end_date', 'budget_amount', 'currency_code',
            'client_name', 'manager_name', 'created_by_name',
            'total_expenses', 'budget_utilization_percent',
            'is_active', 'created_at'
        ]
    
    def get_client_name(self, obj):
        if obj.client:
            return obj.client.company_name or obj.client.contact_name
        return None


class ProjectCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating projects"""
    
    class Meta:
        model = Project
        fields = [
            'code', 'name', 'description', 'status',
            'start_date', 'end_date', 'budget_amount', 'currency',
            'client', 'category', 'tags', 'manager', 'notes', 'settings'
        ]
    
    def validate_code(self, value):
        if not value:
            raise serializers.ValidationError(_("Project code is required."))
        if Project.objects.filter(code=value).exists():
            raise serializers.ValidationError(
                _("A project with code '%(code)s' already exists.") % {'code': value}
            )
        return value
    
    def validate_name(self, value):
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError(_("Project name must be at least 2 characters."))
        return value.strip()
    
    def create(self, validated_data):
        # Set tenant and created_by from request context
        request = self.context.get('request')
        if request:
            validated_data['created_by'] = request.user
            if hasattr(request, 'tenant'):
                validated_data['tenant'] = request.tenant
        return super().create(validated_data)


class ProjectUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating projects"""
    
    class Meta:
        model = Project
        fields = [
            'name', 'description', 'status',
            'start_date', 'end_date', 'budget_amount', 'currency',
            'client', 'category', 'tags', 'manager', 'notes', 'settings',
            'is_active'
        ]
    
    def validate_name(self, value):
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError(_("Project name must be at least 2 characters."))
        return value.strip()


class LinkDocumentToProjectSerializer(serializers.Serializer):
    """Serializer for linking existing documents to a project"""
    document_type = serializers.ChoiceField(
        choices=['expense', 'invoice', 'journal_entry'],
        help_text=_("Type of document to link")
    )
    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text=_("List of document IDs to link")
    )
    
    def validate(self, data):
        document_type = data['document_type']
        document_ids = data['document_ids']
        
        # Verify all documents exist
        if document_type == 'expense':
            existing = Expense.objects.filter(id__in=document_ids).count()
        elif document_type == 'invoice':
            existing = Invoice.objects.filter(id__in=document_ids).count()
        elif document_type == 'journal_entry':
            existing = JournalEntry.objects.filter(id__in=document_ids).count()
        
        if existing != len(document_ids):
            raise serializers.ValidationError(
                _("Some documents were not found.")
            )
        
        return data
