from django.db import models
from django.conf import settings
from core.models import BaseModel
import uuid


class ReceiptStatus(models.TextChoices):
    """Receipt processing status / 收據處理狀態"""
    UPLOADED = 'UPLOADED', 'Uploaded / 已上傳'
    ANALYZING = 'ANALYZING', 'Analyzing / 分析中'
    ANALYZED = 'ANALYZED', 'Analyzed / 已分析'
    CATEGORIZED = 'CATEGORIZED', 'Categorized / 已分類'
    JOURNAL_CREATED = 'JOURNAL_CREATED', 'Journal Created / 已建分錄'
    APPROVED = 'APPROVED', 'Approved / 已核准'
    POSTED = 'POSTED', 'Posted / 已過帳'
    REJECTED = 'REJECTED', 'Rejected / 已拒絕'
    ERROR = 'ERROR', 'Error / 錯誤'


class ExpenseCategory(models.TextChoices):
    """Expense categories / 費用類別"""
    MEALS = 'MEALS', 'Meals / 伙食費'
    TRANSPORTATION = 'TRANSPORTATION', 'Transportation / 交通費'
    OFFICE_SUPPLIES = 'OFFICE_SUPPLIES', 'Office Supplies / 辦公用品'
    UTILITIES = 'UTILITIES', 'Utilities / 水電費'
    ENTERTAINMENT = 'ENTERTAINMENT', 'Entertainment / 交際費'
    RENT = 'RENT', 'Rent / 租金'
    TELEPHONE = 'TELEPHONE', 'Telephone / 電話費'
    INSURANCE = 'INSURANCE', 'Insurance / 保險費'
    MAINTENANCE = 'MAINTENANCE', 'Maintenance / 維修費'
    TRAVEL = 'TRAVEL', 'Travel / 差旅費'
    TRAINING = 'TRAINING', 'Training / 培訓費'
    OTHER = 'OTHER', 'Other / 其他'


class Receipt(BaseModel):
    """
    Receipt model for storing uploaded receipts and AI analysis results
    收據模型 - 存儲上傳的收據和AI分析結果
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Upload info / 上傳資訊
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='receipts'
    )
    image = models.ImageField(upload_to='receipts/%Y/%m/')
    image_base64 = models.TextField(blank=True, null=True)  # Cached base64
    original_filename = models.CharField(max_length=255, blank=True)
    
    # Status / 狀態
    status = models.CharField(
        max_length=20,
        choices=ReceiptStatus.choices,
        default=ReceiptStatus.UPLOADED
    )
    
    # Extracted data / 提取的數據
    vendor_name = models.CharField(max_length=255, blank=True, null=True)
    vendor_address = models.TextField(blank=True, null=True)
    vendor_phone = models.CharField(max_length=50, blank=True, null=True)
    vendor_tax_id = models.CharField(max_length=50, blank=True, null=True)
    
    receipt_number = models.CharField(max_length=100, blank=True, null=True)
    receipt_date = models.DateField(blank=True, null=True)
    receipt_time = models.TimeField(blank=True, null=True)
    
    # Amounts / 金額
    currency = models.CharField(max_length=10, default='TWD')
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Payment / 付款
    payment_method = models.CharField(max_length=20, default='CASH')
    
    # Categorization / 分類
    category = models.CharField(
        max_length=30,
        choices=ExpenseCategory.choices,
        default=ExpenseCategory.OTHER
    )
    description = models.TextField(blank=True, null=True)
    
    # Line items (JSON) / 明細項目
    items = models.JSONField(default=list, blank=True)
    
    # AI Analysis / AI分析
    ai_raw_response = models.JSONField(default=dict, blank=True)
    ai_confidence_score = models.FloatField(default=0)
    ai_suggestions = models.JSONField(default=list, blank=True)
    ai_warnings = models.JSONField(default=list, blank=True)
    detected_language = models.CharField(max_length=10, default='auto')
    
    # Journal Entry / 會計分錄
    journal_entry_data = models.JSONField(default=dict, blank=True)
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipts'
    )
    
    # Expense link / 費用連結
    expense = models.ForeignKey(
        'accounting.Expense',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipts'
    )
    
    # Notes / 備註
    notes = models.TextField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_receipts'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Receipt / 收據'
        verbose_name_plural = 'Receipts / 收據'
    
    def __str__(self):
        return f"{self.receipt_number or self.id} - {self.vendor_name or 'Unknown'} - {self.total_amount}"


class ReceiptComparison(BaseModel):
    """
    Receipt comparison results for Excel vs Database
    收據比對結果 - Excel與資料庫對比
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='receipt_comparisons'
    )
    
    # Uploaded Excel / 上傳的Excel
    excel_file = models.FileField(upload_to='comparisons/%Y/%m/')
    excel_filename = models.CharField(max_length=255)
    
    # Comparison results / 比對結果
    total_excel_records = models.IntegerField(default=0)
    total_db_records = models.IntegerField(default=0)
    matched_count = models.IntegerField(default=0)
    missing_in_db_count = models.IntegerField(default=0)
    missing_in_excel_count = models.IntegerField(default=0)
    amount_mismatch_count = models.IntegerField(default=0)
    
    # Detailed results / 詳細結果
    comparison_details = models.JSONField(default=dict)
    ai_analysis = models.JSONField(default=dict)
    
    # Status / 狀態
    status = models.CharField(max_length=20, default='PENDING')
    health_score = models.FloatField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Receipt Comparison / 收據比對'
        verbose_name_plural = 'Receipt Comparisons / 收據比對'


class ExpenseReport(BaseModel):
    """
    Generated expense reports for manager approval
    生成的費用報表供主管簽核
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    report_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expense_reports'
    )
    
    # Report period / 報表期間
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Receipts included / 包含的收據
    receipts = models.ManyToManyField(Receipt, related_name='reports')
    
    # Totals / 總計
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_count = models.IntegerField(default=0)
    
    # Generated files / 生成的檔案
    excel_file = models.FileField(upload_to='reports/%Y/%m/', null=True, blank=True)
    pdf_file = models.FileField(upload_to='reports/%Y/%m/', null=True, blank=True)
    
    # Approval workflow / 審批流程
    status = models.CharField(max_length=20, default='DRAFT')
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_reports'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Expense Report / 費用報表'
        verbose_name_plural = 'Expense Reports / 費用報表'
    
    def __str__(self):
        return f"{self.report_number} - {self.title}"


# Import extended AI models for convenience
from .models_extended import (
    # Email Assistant
    EmailStatus,
    EmailCategory,
    EmailPriority,
    EmailAccount,
    Email,
    EmailAttachment,
    EmailTemplate,
    # Planner AI
    TaskPriority,
    TaskStatus,
    PlannerTask,
    ScheduleEvent,
    # Document Assistant
    DocumentType,
    AIDocument,
    DocumentComparison,
    # Brainstorming Assistant
    BrainstormSession,
    BrainstormIdea,
)