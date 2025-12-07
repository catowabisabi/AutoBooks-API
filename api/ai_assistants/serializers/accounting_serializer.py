"""
Accounting Assistant Serializers
會計助手序列化器
"""

from rest_framework import serializers
from ai_assistants.models import (
    Receipt, ReceiptComparison, ExpenseReport, 
    AccountingProject, FieldExtraction,
    ReceiptStatus, ProjectType, ProjectStatus
)
from business.models import Company


class ReceiptItemSerializer(serializers.Serializer):
    """Serializer for receipt line items / 收據明細序列化器"""
    description = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = serializers.DecimalField(max_digits=15, decimal_places=2)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    tax_included = serializers.BooleanField(default=True)


class ReceiptSerializer(serializers.ModelSerializer):
    """Serializer for Receipt model / 收據序列化器"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    is_unrecognized = serializers.BooleanField(read_only=True)
    needs_review = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'project', 'project_name', 'status', 'uploaded_by', 'uploaded_by_name',
            'image', 'original_filename', 'unrecognized_reason',
            'is_unrecognized', 'needs_review',
            'vendor_name', 'vendor_address', 'vendor_phone', 'vendor_tax_id',
            'receipt_number', 'receipt_date', 'receipt_time',
            'currency', 'subtotal', 'tax_amount', 'tax_rate', 'discount_amount', 'total_amount',
            'payment_method', 'category', 'description', 'items',
            'ai_confidence_score', 'ai_suggestions', 'ai_warnings', 'detected_language',
            'journal_entry_data', 'journal_entry', 'expense',
            'notes', 'reviewed_by', 'reviewed_by_name', 'reviewed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at', 'updated_at']


class ReceiptUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating receipt / 更新收據序列化器"""
    
    class Meta:
        model = Receipt
        fields = [
            'project', 'status', 'unrecognized_reason',
            'vendor_name', 'vendor_address', 'vendor_phone', 'vendor_tax_id',
            'receipt_number', 'receipt_date', 'receipt_time',
            'currency', 'subtotal', 'tax_amount', 'tax_rate', 'discount_amount', 'total_amount',
            'payment_method', 'category', 'description', 'items', 'notes'
        ]


class JournalEntryLineSerializer(serializers.Serializer):
    """Serializer for journal entry lines / 分錄行序列化器"""
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    debit = serializers.DecimalField(max_digits=15, decimal_places=2)
    credit = serializers.DecimalField(max_digits=15, decimal_places=2)


class JournalEntrySerializer(serializers.Serializer):
    """Serializer for generated journal entry / 生成的分錄序列化器"""
    entry_number = serializers.CharField()
    date = serializers.DateField()
    description = serializers.CharField()
    reference = serializers.CharField(required=False, allow_blank=True)
    lines = JournalEntryLineSerializer(many=True)
    total_debit = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    status = serializers.CharField()
    ai_generated = serializers.BooleanField()


class AIReviewSerializer(serializers.Serializer):
    """Serializer for AI review results / AI審核結果序列化器"""
    validation_status = serializers.CharField()
    validation_issues = serializers.ListField(child=serializers.CharField(), required=False)
    categorization_review = serializers.DictField(required=False)
    tax_compliance = serializers.DictField(required=False)
    suggestions = serializers.ListField(required=False)
    anomalies = serializers.ListField(child=serializers.CharField(), required=False)
    overall_score = serializers.FloatField()
    summary = serializers.CharField(required=False)


class ReceiptProcessResultSerializer(serializers.Serializer):
    """Serializer for full receipt processing result / 完整收據處理結果序列化器"""
    status = serializers.CharField()
    steps = serializers.ListField()
    receipt_data = serializers.DictField(required=False)
    categorization = serializers.DictField(required=False)
    journal_entry = JournalEntrySerializer(required=False)
    ai_suggestions = AIReviewSerializer(required=False)
    error = serializers.CharField(required=False)


class ExcelCompareSerializer(serializers.Serializer):
    """Serializer for Excel comparison / Excel比對序列化器"""
    excel_file = serializers.FileField()
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


class ReceiptComparisonSerializer(serializers.ModelSerializer):
    """Serializer for comparison results / 比對結果序列化器"""
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    class Meta:
        model = ReceiptComparison
        fields = [
            'id', 'created_by', 'created_by_name',
            'excel_file', 'excel_filename',
            'total_excel_records', 'total_db_records', 'matched_count',
            'missing_in_db_count', 'missing_in_excel_count', 'amount_mismatch_count',
            'comparison_details', 'ai_analysis',
            'status', 'health_score',
            'created_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at']


class ExpenseReportCreateSerializer(serializers.Serializer):
    """Serializer for creating expense report / 建立費用報表序列化器"""
    title = serializers.CharField(max_length=255)
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    receipt_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    include_all = serializers.BooleanField(default=False)


class ExpenseReportSerializer(serializers.ModelSerializer):
    """Serializer for expense report / 費用報表序列化器"""
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)
    receipt_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ExpenseReport
        fields = [
            'id', 'report_number', 'title',
            'created_by', 'created_by_name',
            'period_start', 'period_end',
            'total_amount', 'total_tax', 'total_count', 'receipt_count',
            'excel_file', 'pdf_file',
            'status', 'submitted_at',
            'approved_by', 'approved_by_name', 'approved_at', 'approval_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'report_number', 'created_by', 'created_at', 'updated_at']
    
    def get_receipt_count(self, obj):
        return obj.receipts.count()


class AIQuerySerializer(serializers.Serializer):
    """Serializer for AI query / AI查詢序列化器"""
    query = serializers.CharField()
    context = serializers.CharField(required=False, allow_blank=True)
    receipt_id = serializers.UUIDField(required=False)
    include_suggestions = serializers.BooleanField(default=True)


# =================================================================
# Accounting Project Serializers / 會計專案序列化器
# =================================================================

class AccountingProjectListSerializer(serializers.ModelSerializer):
    """Serializer for listing accounting projects / 會計專案列表序列化器"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    receipt_count = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = AccountingProject
        fields = [
            'id', 'code', 'name', 'company', 'company_name',
            'project_type', 'status', 'fiscal_year', 'quarter',
            'start_date', 'end_date', 'deadline',
            'owner', 'owner_name', 'progress',
            'receipt_count', 'is_overdue',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_receipt_count(self, obj):
        return obj.receipts.count()


class AccountingProjectDetailSerializer(serializers.ModelSerializer):
    """Serializer for accounting project detail / 會計專案詳情序列化器"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    team_member_names = serializers.SerializerMethodField()
    receipt_count = serializers.SerializerMethodField()
    receipt_stats = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = AccountingProject
        fields = [
            'id', 'code', 'name', 'description',
            'company', 'company_name',
            'project_type', 'status', 'fiscal_year', 'quarter',
            'start_date', 'end_date', 'deadline',
            'owner', 'owner_name', 'team_members', 'team_member_names',
            'progress', 'budget_hours', 'actual_hours',
            'receipt_count', 'receipt_stats',
            'notes', 'is_overdue',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_team_member_names(self, obj):
        return [m.full_name for m in obj.team_members.all()]
    
    def get_receipt_count(self, obj):
        return obj.receipts.count()
    
    def get_receipt_stats(self, obj):
        """Return receipt statistics by status"""
        from django.db.models import Count
        stats = obj.receipts.values('status').annotate(count=Count('id'))
        return {s['status']: s['count'] for s in stats}


class AccountingProjectCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating accounting project / 建立會計專案序列化器"""
    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        required=False,
        allow_null=True
    )
    company_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = AccountingProject
        fields = [
            'code', 'name', 'description', 'company', 'company_name',
            'project_type', 'fiscal_year', 'quarter',
            'start_date', 'end_date', 'deadline',
            'team_members', 'budget_hours', 'notes'
        ]
    
    def validate_code(self, value):
        if AccountingProject.objects.filter(code=value).exists():
            raise serializers.ValidationError("Project code already exists / 專案編號已存在")
        return value
    
    def validate(self, attrs):
        company = attrs.get('company')
        company_name = attrs.get('company_name', '').strip()
        
        # If no company but company_name provided, create or get company
        if not company and company_name:
            company, _ = Company.objects.get_or_create(
                name=company_name,
                defaults={'contact_person': '', 'contact_email': '', 'contact_phone': ''}
            )
            attrs['company'] = company
        elif not company and not company_name:
            # Allow creation without company - use project name as company name
            project_name = attrs.get('name', 'Unnamed Project')
            company, _ = Company.objects.get_or_create(
                name=project_name,
                defaults={'contact_person': '', 'contact_email': '', 'contact_phone': ''}
            )
            attrs['company'] = company
        
        # Remove company_name from attrs as it's not a model field
        attrs.pop('company_name', None)
        return attrs
    
    def create(self, validated_data):
        team_members = validated_data.pop('team_members', [])
        validated_data['owner'] = self.context['request'].user
        validated_data['status'] = ProjectStatus.DRAFT
        project = AccountingProject.objects.create(**validated_data)
        project.team_members.set(team_members)
        return project


class AccountingProjectUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating accounting project / 更新會計專案序列化器"""
    
    class Meta:
        model = AccountingProject
        fields = [
            'name', 'description', 'status',
            'start_date', 'end_date', 'deadline',
            'team_members', 'progress', 'budget_hours', 'actual_hours', 'notes'
        ]


# =================================================================
# Field Extraction Serializers / 欄位提取序列化器
# =================================================================

class FieldExtractionSerializer(serializers.ModelSerializer):
    """Serializer for field extraction / 欄位提取序列化器"""
    verified_by_name = serializers.CharField(source='verified_by.full_name', read_only=True)
    final_value = serializers.CharField(read_only=True)
    needs_review = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = FieldExtraction
        fields = [
            'id', 'receipt', 'field_name',
            'extracted_value', 'corrected_value', 'final_value',
            'confidence', 'bounding_box',
            'is_verified', 'verified_by', 'verified_by_name', 'verified_at',
            'needs_review',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'receipt', 'field_name', 'extracted_value', 'created_at', 'updated_at']


class FieldCorrectionSerializer(serializers.Serializer):
    """Serializer for correcting extracted fields / 校正提取欄位序列化器"""
    field_id = serializers.UUIDField()
    corrected_value = serializers.CharField()
    mark_verified = serializers.BooleanField(default=True)


class BulkFieldCorrectionSerializer(serializers.Serializer):
    """Serializer for bulk field corrections / 批量校正序列化器"""
    corrections = FieldCorrectionSerializer(many=True)


# =================================================================
# Unrecognized Document Serializers / 無法識別文件序列化器
# =================================================================

class UnrecognizedReceiptSerializer(serializers.ModelSerializer):
    """Serializer for unrecognized receipts / 無法識別收據序列化器"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'project', 'project_name',
            'uploaded_by', 'uploaded_by_name',
            'image', 'original_filename',
            'status', 'unrecognized_reason',
            'ai_confidence_score', 'ai_warnings',
            'created_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at']


class ManualClassificationSerializer(serializers.Serializer):
    """Serializer for manual document classification / 手動分類序列化器"""
    receipt_id = serializers.UUIDField()
    vendor_name = serializers.CharField(required=False)
    receipt_date = serializers.DateField(required=False)
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    category = serializers.ChoiceField(choices=[], required=False)  # Will be set dynamically
    new_status = serializers.ChoiceField(
        choices=[
            (ReceiptStatus.PENDING_REVIEW, 'Pending Review'),
            (ReceiptStatus.CATEGORIZED, 'Categorized'),
        ],
        default=ReceiptStatus.PENDING_REVIEW
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ai_assistants.models import ExpenseCategory
        self.fields['category'].choices = ExpenseCategory.choices


class BulkStatusUpdateSerializer(serializers.Serializer):
    """Serializer for bulk status update / 批量狀態更新序列化器"""
    receipt_ids = serializers.ListField(child=serializers.UUIDField())
    new_status = serializers.ChoiceField(choices=ReceiptStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)


# =================================================================
# Receipt Upload with Project / 帶專案的收據上傳
# =================================================================

class ReceiptUploadSerializer(serializers.Serializer):
    """Serializer for receipt upload / 收據上傳序列化器"""
    image = serializers.ImageField(required=False)
    image_base64 = serializers.CharField(required=False)
    project_id = serializers.UUIDField(required=False, help_text='Associated project ID')
    language = serializers.ChoiceField(
        choices=['auto', 'en', 'zh-TW', 'zh-CN', 'ja'],
        default='auto'
    )
    auto_categorize = serializers.BooleanField(default=True)
    auto_journal = serializers.BooleanField(default=False)
    
    def validate(self, data):
        if not data.get('image') and not data.get('image_base64'):
            raise serializers.ValidationError("Either 'image' or 'image_base64' is required")
        return data


class BulkReceiptUploadSerializer(serializers.Serializer):
    """Serializer for bulk receipt upload / 批量收據上傳序列化器"""
    files = serializers.ListField(
        child=serializers.ImageField(),
        max_length=50,
        help_text='Maximum 50 files per upload'
    )
    project_id = serializers.UUIDField(required=False)
    language = serializers.ChoiceField(
        choices=['auto', 'en', 'zh-TW', 'zh-CN', 'ja'],
        default='auto'
    )
    auto_categorize = serializers.BooleanField(default=True)
