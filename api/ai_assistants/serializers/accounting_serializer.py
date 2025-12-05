"""
Accounting Assistant Serializers
會計助手序列化器
"""

from rest_framework import serializers
from ai_assistants.models import Receipt, ReceiptComparison, ExpenseReport


class ReceiptUploadSerializer(serializers.Serializer):
    """Serializer for receipt upload / 收據上傳序列化器"""
    image = serializers.ImageField(required=False)
    image_base64 = serializers.CharField(required=False)
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
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'status', 'uploaded_by', 'uploaded_by_name',
            'image', 'original_filename',
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
