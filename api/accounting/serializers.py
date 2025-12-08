from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import (
    FiscalYear, AccountingPeriod, Currency, TaxRate, Account,
    JournalEntry, JournalEntryLine, Contact, Invoice, InvoiceLine,
    Payment, PaymentAllocation, Expense, Project, ProjectDocument,
    ProjectStatus, Receipt, RecognitionStatus,
    ExtractedField, ExtractedFieldType, FieldCorrectionHistory, ReceiptCorrectionSummary,
    Report, ReportTemplate, ReportExport, ReportSchedule, ReportSection,
    ReportType, ReportStatus, ExportFormat
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


# =================================================================
# Receipt Serializers
# =================================================================

class ReceiptSerializer(serializers.ModelSerializer):
    """Full serializer for receipt details"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    classified_by_name = serializers.CharField(source='classified_by.full_name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    project_code = serializers.CharField(source='project.code', read_only=True)
    expense_number = serializers.CharField(source='expense.expense_number', read_only=True)
    category_name = serializers.CharField(source='manual_category.name', read_only=True)
    category_code = serializers.CharField(source='manual_category.code', read_only=True)
    final_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    final_vendor = serializers.CharField(read_only=True)
    final_date = serializers.DateField(read_only=True)
    is_recognized = serializers.BooleanField(read_only=True)
    needs_manual_review = serializers.BooleanField(read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'file', 'file_url', 'original_filename', 'file_size', 'mime_type',
            'recognition_status', 'confidence_score', 'confidence_threshold',
            'extracted_data', 'vendor_name', 'receipt_date', 'total_amount',
            'currency_code', 'tax_amount', 'description',
            'manual_category', 'category_name', 'category_code',
            'manual_vendor', 'manual_amount', 'manual_date',
            'classification_notes', 'classified_by', 'classified_by_name', 'classified_at',
            'project', 'project_name', 'project_code', 'expense', 'expense_number',
            'processing_started_at', 'processing_completed_at', 'processing_error',
            'retry_count', 'uploaded_by', 'uploaded_by_name', 'batch_id', 'tags',
            'final_amount', 'final_vendor', 'final_date',
            'is_recognized', 'needs_manual_review',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_size', 'mime_type', 'extracted_data',
            'processing_started_at', 'processing_completed_at',
            'uploaded_by', 'batch_id', 'created_at', 'updated_at'
        ]
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class ReceiptListSerializer(serializers.ModelSerializer):
    """Simplified serializer for receipt lists"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    category_name = serializers.CharField(source='manual_category.name', read_only=True)
    final_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    final_vendor = serializers.CharField(read_only=True)
    final_date = serializers.DateField(read_only=True)
    needs_manual_review = serializers.BooleanField(read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'file_url', 'original_filename', 'file_size',
            'recognition_status', 'confidence_score',
            'final_amount', 'final_vendor', 'final_date',
            'project', 'project_name', 'category_name',
            'uploaded_by_name', 'batch_id',
            'needs_manual_review', 'created_at'
        ]
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class ReceiptUploadSerializer(serializers.Serializer):
    """Serializer for single receipt upload"""
    file = serializers.FileField()
    project_id = serializers.UUIDField(required=False, allow_null=True)
    auto_process = serializers.BooleanField(default=True, help_text='Auto process OCR extraction')
    confidence_threshold = serializers.DecimalField(
        max_digits=5, decimal_places=4,
        default='0.7000',
        help_text='Minimum confidence for recognition'
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )
    
    def validate_file(self, value):
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                _("Invalid file type. Allowed: JPEG, PNG, GIF, WebP, PDF")
            )
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                _("File size exceeds maximum of 10MB")
            )
        return value


class BulkReceiptUploadSerializer(serializers.Serializer):
    """Serializer for bulk receipt upload"""
    files = serializers.ListField(
        child=serializers.FileField(),
        max_length=50,
        help_text='Maximum 50 files per upload'
    )
    project_id = serializers.UUIDField(required=False, allow_null=True)
    auto_process = serializers.BooleanField(default=True)
    confidence_threshold = serializers.DecimalField(
        max_digits=5, decimal_places=4,
        default='0.7000'
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )
    
    def validate_files(self, value):
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf']
        max_size = 10 * 1024 * 1024
        errors = []
        
        for i, file in enumerate(value):
            if file.content_type not in allowed_types:
                errors.append(f"File {i+1} ({file.name}): Invalid file type")
            if file.size > max_size:
                errors.append(f"File {i+1} ({file.name}): Exceeds 10MB limit")
        
        if errors:
            raise serializers.ValidationError(errors)
        return value


class ReceiptClassifySerializer(serializers.Serializer):
    """Serializer for manual receipt classification"""
    category_id = serializers.UUIDField(required=False, allow_null=True)
    vendor = serializers.CharField(max_length=255, required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False
    )
    
    def validate_category_id(self, value):
        if value:
            from .models import Account, AccountType
            try:
                account = Account.objects.get(id=value)
                if account.account_type != AccountType.EXPENSE.value:
                    raise serializers.ValidationError(
                        _("Category must be an expense account")
                    )
            except Account.DoesNotExist:
                raise serializers.ValidationError(_("Category not found"))
        return value


class BulkReceiptClassifySerializer(serializers.Serializer):
    """Serializer for batch receipt classification"""
    receipt_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text='List of receipt IDs to classify'
    )
    category_id = serializers.UUIDField(required=False, allow_null=True)
    project_id = serializers.UUIDField(required=False, allow_null=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_receipt_ids(self, value):
        existing = Receipt.objects.filter(id__in=value).count()
        if existing != len(value):
            raise serializers.ValidationError(
                _("Some receipts were not found")
            )
        return value
    
    def validate_category_id(self, value):
        if value:
            from .models import Account, AccountType
            try:
                account = Account.objects.get(id=value)
                if account.account_type != AccountType.EXPENSE.value:
                    raise serializers.ValidationError(
                        _("Category must be an expense account")
                    )
            except Account.DoesNotExist:
                raise serializers.ValidationError(_("Category not found"))
        return value
    
    def validate_project_id(self, value):
        if value:
            if not Project.objects.filter(id=value).exists():
                raise serializers.ValidationError(_("Project not found"))
        return value


class BulkReceiptStatusUpdateSerializer(serializers.Serializer):
    """Serializer for bulk status update"""
    receipt_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    status = serializers.ChoiceField(choices=RecognitionStatus.choices())
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_receipt_ids(self, value):
        existing = Receipt.objects.filter(id__in=value).count()
        if existing != len(value):
            raise serializers.ValidationError(
                _("Some receipts were not found")
            )
        return value


class ReceiptProcessingResultSerializer(serializers.Serializer):
    """Serializer for receipt processing result"""
    id = serializers.UUIDField()
    original_filename = serializers.CharField()
    recognition_status = serializers.CharField()
    confidence_score = serializers.DecimalField(max_digits=5, decimal_places=4, allow_null=True)
    vendor_name = serializers.CharField(allow_blank=True)
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    receipt_date = serializers.DateField(allow_null=True)
    error = serializers.CharField(allow_blank=True, required=False)


class BulkUploadProgressSerializer(serializers.Serializer):
    """Serializer for bulk upload progress response"""
    batch_id = serializers.UUIDField()
    total_files = serializers.IntegerField()
    processed = serializers.IntegerField()
    recognized = serializers.IntegerField()
    unrecognized = serializers.IntegerField()
    failed = serializers.IntegerField()
    results = ReceiptProcessingResultSerializer(many=True)


# =================================================================
# Extracted Field Serializers with Bounding Box Support
# =================================================================

class BoundingBoxSerializer(serializers.Serializer):
    """Serializer for bounding box coordinates"""
    x1 = serializers.FloatField(min_value=0, help_text='Left coordinate')
    y1 = serializers.FloatField(min_value=0, help_text='Top coordinate')
    x2 = serializers.FloatField(min_value=0, help_text='Right coordinate')
    y2 = serializers.FloatField(min_value=0, help_text='Bottom coordinate')
    
    def validate(self, data):
        if data.get('x2', 0) < data.get('x1', 0):
            raise serializers.ValidationError(_("x2 must be greater than or equal to x1"))
        if data.get('y2', 0) < data.get('y1', 0):
            raise serializers.ValidationError(_("y2 must be greater than or equal to y1"))
        return data


class ExtractedFieldSerializer(serializers.ModelSerializer):
    """Full serializer for extracted field with bounding box"""
    final_value = serializers.CharField(read_only=True)
    final_bbox = serializers.DictField(read_only=True)
    has_bbox = serializers.BooleanField(read_only=True)
    corrected_by_name = serializers.CharField(source='corrected_by.full_name', read_only=True)
    
    class Meta:
        model = ExtractedField
        fields = [
            'id', 'receipt', 'field_type', 'field_name',
            'raw_value', 'normalized_value', 'data_type',
            'bbox_x1', 'bbox_y1', 'bbox_x2', 'bbox_y2', 'bbox_unit', 'page_number',
            'confidence_score',
            'is_corrected', 'corrected_value',
            'corrected_bbox_x1', 'corrected_bbox_y1', 'corrected_bbox_x2', 'corrected_bbox_y2',
            'corrected_by', 'corrected_by_name', 'corrected_at',
            'version',
            'final_value', 'final_bbox', 'has_bbox',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'receipt', 'version', 'corrected_by', 'corrected_at',
            'created_at', 'updated_at'
        ]


class ExtractedFieldListSerializer(serializers.ModelSerializer):
    """Simplified serializer for field lists"""
    final_value = serializers.CharField(read_only=True)
    final_bbox = serializers.DictField(read_only=True)
    
    class Meta:
        model = ExtractedField
        fields = [
            'id', 'field_type', 'field_name',
            'final_value', 'confidence_score',
            'is_corrected', 'version',
            'final_bbox'
        ]


class FieldCorrectionHistorySerializer(serializers.ModelSerializer):
    """Serializer for field correction history (audit trail)"""
    corrected_by_name = serializers.CharField(source='corrected_by.full_name', read_only=True)
    field_type = serializers.CharField(source='extracted_field.field_type', read_only=True)
    field_name = serializers.CharField(source='extracted_field.field_name', read_only=True)
    
    class Meta:
        model = FieldCorrectionHistory
        fields = [
            'id', 'extracted_field', 'field_type', 'field_name', 'version',
            'previous_value', 'previous_bbox_x1', 'previous_bbox_y1',
            'previous_bbox_x2', 'previous_bbox_y2',
            'new_value', 'new_bbox_x1', 'new_bbox_y1',
            'new_bbox_x2', 'new_bbox_y2',
            'correction_reason', 'corrected_by', 'corrected_by_name',
            'corrected_at', 'correction_source'
        ]
        read_only_fields = ['id', 'corrected_at']


class ReceiptCorrectionSummarySerializer(serializers.ModelSerializer):
    """Serializer for receipt correction summary"""
    
    class Meta:
        model = ReceiptCorrectionSummary
        fields = [
            'total_fields', 'corrected_fields', 'total_corrections',
            'first_corrected_at', 'last_corrected_at',
            'corrected_by_users', 'original_avg_confidence'
        ]


class FieldCorrectionInputSerializer(serializers.Serializer):
    """Input serializer for correcting a single field"""
    field_id = serializers.UUIDField(required=False, help_text='ID of existing field to correct')
    field_type = serializers.ChoiceField(
        choices=ExtractedFieldType.choices(),
        required=False,
        help_text='Type of field (required for new fields)'
    )
    field_name = serializers.CharField(max_length=100, required=False)
    
    # New value
    value = serializers.CharField(allow_blank=True, required=False)
    
    # Bounding box (optional)
    bbox = BoundingBoxSerializer(required=False, allow_null=True)
    
    # Correction metadata
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if not data.get('field_id') and not data.get('field_type'):
            raise serializers.ValidationError(
                _("Either field_id (for existing field) or field_type (for new field) is required")
            )
        return data


class ReceiptCorrectSerializer(serializers.Serializer):
    """
    Main serializer for PUT /receipts/{id}/correct endpoint.
    Allows correcting multiple fields at once with version history.
    """
    fields = serializers.ListField(
        child=FieldCorrectionInputSerializer(),
        min_length=1,
        help_text='List of field corrections to apply'
    )
    correction_source = serializers.ChoiceField(
        choices=['MANUAL', 'AI_SUGGESTION', 'BATCH_UPDATE'],
        default='MANUAL'
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_fields(self, value):
        # Validate field_ids if provided
        field_ids = [f.get('field_id') for f in value if f.get('field_id')]
        if field_ids:
            existing_count = ExtractedField.objects.filter(id__in=field_ids).count()
            if existing_count != len(field_ids):
                raise serializers.ValidationError(
                    _("Some field IDs were not found")
                )
        return value


class BulkFieldCorrectionSerializer(serializers.Serializer):
    """Serializer for bulk field corrections across multiple receipts"""
    corrections = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    correction_source = serializers.ChoiceField(
        choices=['MANUAL', 'AI_SUGGESTION', 'BATCH_UPDATE'],
        default='BATCH_UPDATE'
    )
    
    def validate_corrections(self, value):
        for i, correction in enumerate(value):
            if 'receipt_id' not in correction:
                raise serializers.ValidationError(
                    _("Each correction must include receipt_id")
                )
            if 'fields' not in correction or not correction['fields']:
                raise serializers.ValidationError(
                    _("Each correction must include at least one field")
                )
        return value


class ReceiptWithFieldsSerializer(serializers.ModelSerializer):
    """Receipt serializer that includes extracted fields with bounding boxes"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    classified_by_name = serializers.CharField(source='classified_by.full_name', read_only=True)
    extracted_fields = ExtractedFieldListSerializer(many=True, read_only=True)
    correction_summary = ReceiptCorrectionSummarySerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'file', 'file_url', 'original_filename', 'file_size', 'mime_type',
            'recognition_status', 'confidence_score', 'confidence_threshold',
            'vendor_name', 'receipt_date', 'total_amount', 'currency_code', 'tax_amount',
            'manual_category', 'manual_vendor', 'manual_amount', 'manual_date',
            'classification_notes', 'classified_by', 'classified_by_name', 'classified_at',
            'project', 'expense',
            'uploaded_by', 'uploaded_by_name', 'batch_id', 'tags',
            'extracted_fields', 'correction_summary',
            'is_active', 'created_at', 'updated_at'
        ]
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class FieldExtractionResultSerializer(serializers.Serializer):
    """Response serializer for field extraction/correction results"""
    receipt_id = serializers.UUIDField()
    fields_updated = serializers.IntegerField()
    fields_created = serializers.IntegerField()
    correction_history_created = serializers.IntegerField()
    fields = ExtractedFieldListSerializer(many=True)


# =================================================================
# Report Serializers
# =================================================================

class ReportTemplateSerializer(serializers.ModelSerializer):
    """Full serializer for report templates"""
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    report_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'report_type', 'report_type_display',
            'default_filters', 'display_config',
            'include_comparison', 'comparison_type',
            'default_export_format', 'is_public',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_report_type_display(self, obj):
        type_labels = {
            'INCOME_STATEMENT': 'Income Statement',
            'BALANCE_SHEET': 'Balance Sheet',
            'GENERAL_LEDGER': 'General Ledger',
            'SUB_LEDGER': 'Sub-Ledger',
            'TRIAL_BALANCE': 'Trial Balance',
            'CASH_FLOW': 'Cash Flow Statement',
            'ACCOUNTS_RECEIVABLE': 'Accounts Receivable Aging',
            'ACCOUNTS_PAYABLE': 'Accounts Payable Aging',
            'EXPENSE_REPORT': 'Expense Report',
            'TAX_SUMMARY': 'Tax Summary',
            'CUSTOM': 'Custom Report',
        }
        return type_labels.get(obj.report_type, obj.report_type)


class ReportTemplateListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing templates"""
    class Meta:
        model = ReportTemplate
        fields = ['id', 'name', 'report_type', 'is_public', 'created_at']


class ReportSectionSerializer(serializers.ModelSerializer):
    """Serializer for report sections"""
    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportSection
        fields = [
            'id', 'section_type', 'title', 'sequence',
            'account', 'account_code', 'account_name',
            'data', 'debit_total', 'credit_total', 'balance',
            'comparison_balance', 'variance', 'variance_percent',
            'children'
        ]
    
    def get_children(self, obj):
        children = obj.children.all().order_by('sequence')
        return ReportSectionSerializer(children, many=True).data


class ReportExportSerializer(serializers.ModelSerializer):
    """Serializer for report exports"""
    exported_by_name = serializers.CharField(source='exported_by.full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ReportExport
        fields = [
            'id', 'report', 'export_format', 'file', 'file_url',
            'file_name', 'file_size', 'mime_type',
            'status', 'error_message', 'export_config',
            'expires_at', 'is_expired', 'download_count', 'last_downloaded_at',
            'exported_by', 'exported_by_name',
            'created_at'
        ]
        read_only_fields = [
            'id', 'file', 'file_name', 'file_size', 'mime_type',
            'status', 'error_message', 'download_count', 'last_downloaded_at',
            'exported_by', 'created_at'
        ]
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class ReportExportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing report exports"""
    exported_by_name = serializers.CharField(source='exported_by.full_name', read_only=True)
    report_name = serializers.CharField(source='report.name', read_only=True)
    
    class Meta:
        model = ReportExport
        fields = [
            'id', 'report', 'report_name', 'export_format',
            'file_name', 'file_size', 'status',
            'download_count', 'exported_by_name', 'created_at'
        ]


class ReportSerializer(serializers.ModelSerializer):
    """Full serializer for reports"""
    generated_by_name = serializers.CharField(source='generated_by.full_name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    report_type_display = serializers.SerializerMethodField()
    is_cache_valid = serializers.BooleanField(read_only=True)
    period_display = serializers.CharField(read_only=True)
    sections = ReportSectionSerializer(many=True, read_only=True)
    exports = ReportExportSerializer(many=True, read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'report_number', 'name', 'report_type', 'report_type_display',
            'template', 'template_name',
            'period_start', 'period_end', 'period_display',
            'filters', 'display_config',
            'include_comparison', 'comparison_period_start', 'comparison_period_end',
            'status', 'generation_started_at', 'generation_completed_at', 'generation_error',
            'cached_data', 'summary_totals', 'is_cache_valid',
            'version', 'parent_report', 'is_latest',
            'generated_by', 'generated_by_name',
            'last_viewed_at', 'view_count', 'notes',
            'sections', 'exports',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'report_number', 'status', 'generation_started_at', 
            'generation_completed_at', 'generation_error', 'cached_data',
            'cache_key', 'cache_expires_at', 'data_hash',
            'version', 'is_latest', 'generated_by',
            'last_viewed_at', 'view_count', 'created_at', 'updated_at'
        ]
    
    def get_report_type_display(self, obj):
        type_labels = {
            'INCOME_STATEMENT': 'Income Statement',
            'BALANCE_SHEET': 'Balance Sheet',
            'GENERAL_LEDGER': 'General Ledger',
            'SUB_LEDGER': 'Sub-Ledger',
            'TRIAL_BALANCE': 'Trial Balance',
            'CASH_FLOW': 'Cash Flow Statement',
            'ACCOUNTS_RECEIVABLE': 'Accounts Receivable Aging',
            'ACCOUNTS_PAYABLE': 'Accounts Payable Aging',
            'EXPENSE_REPORT': 'Expense Report',
            'TAX_SUMMARY': 'Tax Summary',
            'CUSTOM': 'Custom Report',
        }
        return type_labels.get(obj.report_type, obj.report_type)


class ReportListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing reports"""
    generated_by_name = serializers.CharField(source='generated_by.full_name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    export_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = [
            'id', 'report_number', 'name', 'report_type',
            'template_name', 'period_start', 'period_end',
            'status', 'summary_totals', 'version', 'is_latest',
            'generated_by_name', 'view_count', 'export_count',
            'created_at'
        ]
    
    def get_export_count(self, obj):
        return obj.exports.count()


class ReportScheduleSerializer(serializers.ModelSerializer):
    """Serializer for report schedules"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    class Meta:
        model = ReportSchedule
        fields = [
            'id', 'name', 'description',
            'template', 'template_name',
            'is_active', 'schedule_type', 'schedule_day', 'schedule_time', 'timezone',
            'period_type', 'auto_export', 'export_formats',
            'send_email', 'email_recipients', 'email_subject_template',
            'last_run_at', 'next_run_at', 'last_run_status', 'run_count',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'last_run_at', 'next_run_at', 'last_run_status', 
            'run_count', 'created_by', 'created_at', 'updated_at'
        ]


# =================================================================
# Report Generation Request Serializers
# =================================================================

class ReportFilterSerializer(serializers.Serializer):
    """Serializer for report filter parameters"""
    project_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )
    vendor_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )
    customer_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )
    account_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )
    account_types = serializers.ListField(
        child=serializers.ChoiceField(choices=['ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE']),
        required=False,
        default=list
    )
    categories = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    include_drafts = serializers.BooleanField(default=False)
    include_voided = serializers.BooleanField(default=False)


class GenerateReportSerializer(serializers.Serializer):
    """Serializer for report generation requests"""
    name = serializers.CharField(max_length=200)
    report_type = serializers.ChoiceField(choices=ReportType.choices())
    template_id = serializers.UUIDField(required=False, allow_null=True)
    
    # Period
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    
    # Filters
    filters = ReportFilterSerializer(required=False)
    
    # Display options
    display_config = serializers.DictField(required=False, default=dict)
    
    # Comparison
    include_comparison = serializers.BooleanField(default=False)
    comparison_period_start = serializers.DateField(required=False, allow_null=True)
    comparison_period_end = serializers.DateField(required=False, allow_null=True)
    
    # Notes
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    
    def validate(self, data):
        if data['period_start'] > data['period_end']:
            raise serializers.ValidationError({
                'period_end': _("End date must be after start date")
            })
        
        if data.get('include_comparison'):
            if not data.get('comparison_period_start') or not data.get('comparison_period_end'):
                raise serializers.ValidationError({
                    'comparison_period_start': _("Comparison period dates are required when comparison is enabled")
                })
            if data['comparison_period_start'] > data['comparison_period_end']:
                raise serializers.ValidationError({
                    'comparison_period_end': _("Comparison end date must be after start date")
                })
        
        return data


class UpdateReportSerializer(serializers.Serializer):
    """Serializer for updating/regenerating an existing report"""
    regenerate_data = serializers.BooleanField(default=False)
    update_period = serializers.BooleanField(default=False)
    period_start = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)
    filters = ReportFilterSerializer(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if data.get('update_period'):
            if not data.get('period_start') or not data.get('period_end'):
                raise serializers.ValidationError({
                    'period_start': _("Period dates are required when updating period")
                })
        return data


class ExportReportSerializer(serializers.Serializer):
    """Serializer for export requests"""
    export_format = serializers.ChoiceField(choices=ExportFormat.choices())
    export_config = serializers.DictField(required=False, default=dict)
    # Config options: 
    # - include_charts: bool
    # - page_orientation: 'portrait' | 'landscape'
    # - paper_size: 'A4' | 'Letter'
    # - include_header: bool
    # - include_footer: bool
    # - company_logo: bool


# =================================================================
# Report Data Response Serializers
# =================================================================

class IncomeStatementLineSerializer(serializers.Serializer):
    """Line item for income statement"""
    account_id = serializers.UUIDField()
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    current_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    comparison_amount = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    variance = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    variance_percent = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)


class IncomeStatementDataSerializer(serializers.Serializer):
    """Income statement report data structure"""
    revenue = serializers.ListField(child=IncomeStatementLineSerializer())
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    cost_of_goods = serializers.ListField(child=IncomeStatementLineSerializer())
    total_cost_of_goods = serializers.DecimalField(max_digits=15, decimal_places=2)
    gross_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    operating_expenses = serializers.ListField(child=IncomeStatementLineSerializer())
    total_operating_expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    operating_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    other_income = serializers.ListField(child=IncomeStatementLineSerializer())
    other_expenses = serializers.ListField(child=IncomeStatementLineSerializer())
    
    income_before_tax = serializers.DecimalField(max_digits=15, decimal_places=2)
    tax_expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Comparison totals
    comparison_total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    comparison_net_income = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)


class BalanceSheetLineSerializer(serializers.Serializer):
    """Line item for balance sheet"""
    account_id = serializers.UUIDField()
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    comparison_balance = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)


class BalanceSheetDataSerializer(serializers.Serializer):
    """Balance sheet report data structure"""
    # Assets
    current_assets = serializers.ListField(child=BalanceSheetLineSerializer())
    total_current_assets = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    fixed_assets = serializers.ListField(child=BalanceSheetLineSerializer())
    total_fixed_assets = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    other_assets = serializers.ListField(child=BalanceSheetLineSerializer())
    total_other_assets = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    total_assets = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Liabilities
    current_liabilities = serializers.ListField(child=BalanceSheetLineSerializer())
    total_current_liabilities = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    long_term_liabilities = serializers.ListField(child=BalanceSheetLineSerializer())
    total_long_term_liabilities = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    total_liabilities = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Equity
    equity = serializers.ListField(child=BalanceSheetLineSerializer())
    retained_earnings = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_equity = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    total_liabilities_and_equity = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Balance check
    is_balanced = serializers.BooleanField()


class GeneralLedgerEntrySerializer(serializers.Serializer):
    """Single entry in general ledger"""
    date = serializers.DateField()
    entry_number = serializers.CharField()
    description = serializers.CharField()
    reference = serializers.CharField(allow_blank=True)
    debit = serializers.DecimalField(max_digits=15, decimal_places=2)
    credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)


class GeneralLedgerAccountSerializer(serializers.Serializer):
    """General ledger for a single account"""
    account_id = serializers.UUIDField()
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    account_type = serializers.CharField()
    opening_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    entries = serializers.ListField(child=GeneralLedgerEntrySerializer())
    total_debits = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_credits = serializers.DecimalField(max_digits=15, decimal_places=2)
    closing_balance = serializers.DecimalField(max_digits=15, decimal_places=2)


class GeneralLedgerDataSerializer(serializers.Serializer):
    """General ledger report data structure"""
    accounts = serializers.ListField(child=GeneralLedgerAccountSerializer())
    total_debits = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_credits = serializers.DecimalField(max_digits=15, decimal_places=2)
    entry_count = serializers.IntegerField()


class ReportDataSerializer(serializers.Serializer):
    """Generic wrapper for report data response"""
    report_type = serializers.CharField()
    report_name = serializers.CharField()
    period_start = serializers.DateField(allow_null=True)
    period_end = serializers.DateField(allow_null=True)
    generated_at = serializers.DateTimeField()
    data = serializers.DictField()
    summary = serializers.DictField(required=False)
    metadata = serializers.DictField(required=False)


