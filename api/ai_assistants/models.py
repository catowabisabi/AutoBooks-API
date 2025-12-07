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
    UNRECOGNIZED = 'UNRECOGNIZED', 'Unrecognized / 無法識別'  # NEW
    PENDING_REVIEW = 'PENDING_REVIEW', 'Pending Review / 待審核'  # NEW
    JOURNAL_CREATED = 'JOURNAL_CREATED', 'Journal Created / 已建分錄'
    APPROVED = 'APPROVED', 'Approved / 已核准'
    POSTED = 'POSTED', 'Posted / 已過帳'
    REJECTED = 'REJECTED', 'Rejected / 已拒絕'
    ERROR = 'ERROR', 'Error / 錯誤'


class ProjectType(models.TextChoices):
    """Accounting project type / 會計專案類型"""
    AUDIT = 'AUDIT', 'Audit / 審計'
    TAX = 'TAX', 'Tax Return / 報稅'
    BOOKKEEPING = 'BOOKKEEPING', 'Bookkeeping / 記帳'
    CONSULTING = 'CONSULTING', 'Consulting / 諮詢'
    OTHER = 'OTHER', 'Other / 其他'


class ProjectStatus(models.TextChoices):
    """Accounting project status / 會計專案狀態"""
    DRAFT = 'DRAFT', 'Draft / 草稿'
    ACTIVE = 'ACTIVE', 'Active / 進行中'
    PENDING_REVIEW = 'PENDING_REVIEW', 'Pending Review / 待審核'
    COMPLETED = 'COMPLETED', 'Completed / 已完成'
    ARCHIVED = 'ARCHIVED', 'Archived / 已歸檔'
    CANCELLED = 'CANCELLED', 'Cancelled / 已取消'


class QuarterChoice(models.IntegerChoices):
    """Fiscal quarter choices / 財務季度"""
    Q1 = 1, 'Q1 / 第一季'
    Q2 = 2, 'Q2 / 第二季'
    Q3 = 3, 'Q3 / 第三季'
    Q4 = 4, 'Q4 / 第四季'


class AccountingProject(BaseModel):
    """
    Accounting project model for managing client projects
    會計專案模型 - 管理客戶專案（審計/報稅/記帳等）
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic info / 基本資訊
    name = models.CharField(max_length=255, help_text='Project name / 專案名稱')
    code = models.CharField(max_length=50, unique=True, help_text='Project code / 專案編號')
    description = models.TextField(blank=True, null=True)
    
    # Company / 公司
    company = models.ForeignKey(
        'business.Company',
        on_delete=models.CASCADE,
        related_name='accounting_projects',
        help_text='Client company / 客戶公司'
    )
    
    # Project type & status / 專案類型與狀態
    project_type = models.CharField(
        max_length=20,
        choices=ProjectType.choices,
        default=ProjectType.BOOKKEEPING
    )
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.DRAFT
    )
    
    # Time period / 時間範圍
    fiscal_year = models.IntegerField(help_text='Fiscal year / 財務年度')
    quarter = models.IntegerField(
        choices=QuarterChoice.choices,
        null=True,
        blank=True,
        help_text='Fiscal quarter (optional) / 財務季度（選填）'
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True, help_text='Project deadline / 截止日期')
    
    # Team / 團隊
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_accounting_projects',
        help_text='Project owner / 專案負責人'
    )
    team_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='accounting_project_memberships',
        blank=True,
        help_text='Team members / 團隊成員'
    )
    
    # Progress / 進度
    progress = models.IntegerField(
        default=0,
        help_text='Progress percentage 0-100 / 進度百分比'
    )
    
    # Budget / 預算
    budget_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Budgeted hours / 預算工時'
    )
    actual_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Actual hours spent / 實際工時'
    )
    
    # Notes / 備註
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-fiscal_year', '-created_at']
        verbose_name = 'Accounting Project / 會計專案'
        verbose_name_plural = 'Accounting Projects / 會計專案'
        indexes = [
            models.Index(fields=['company', 'fiscal_year']),
            models.Index(fields=['status']),
            models.Index(fields=['owner']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.company.name} ({self.fiscal_year})"
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.deadline and self.status not in [ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED, ProjectStatus.CANCELLED]:
            return timezone.now().date() > self.deadline
        return False


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
    
    # Project link / 專案連結
    project = models.ForeignKey(
        AccountingProject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipts',
        help_text='Associated accounting project / 關聯的會計專案'
    )
    
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
    
    # Unrecognized reason / 無法識別原因
    unrecognized_reason = models.TextField(
        blank=True, 
        null=True,
        help_text='Reason why document could not be recognized / 無法識別的原因'
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
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['uploaded_by', 'status']),
            models.Index(fields=['receipt_date']),
        ]
    
    def __str__(self):
        return f"{self.receipt_number or self.id} - {self.vendor_name or 'Unknown'} - {self.total_amount}"
    
    @property
    def is_unrecognized(self):
        return self.status == ReceiptStatus.UNRECOGNIZED
    
    @property
    def needs_review(self):
        return self.status in [ReceiptStatus.PENDING_REVIEW, ReceiptStatus.UNRECOGNIZED]


class FieldExtraction(BaseModel):
    """
    Field extraction with confidence and bounding box for LLM verification
    欄位提取 - 含置信度和邊界框用於校驗
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name='field_extractions'
    )
    
    # Field info / 欄位資訊
    field_name = models.CharField(max_length=100, help_text='Field name (e.g., vendor_name, total_amount)')
    extracted_value = models.TextField(help_text='Extracted value / 提取的值')
    corrected_value = models.TextField(blank=True, null=True, help_text='User corrected value / 用戶校正的值')
    
    # Confidence / 置信度
    confidence = models.FloatField(
        default=0,
        help_text='AI confidence score 0-1 / AI置信度分數'
    )
    
    # Bounding box for highlighting / 高亮用邊界框
    bounding_box = models.JSONField(
        default=dict,
        blank=True,
        help_text='Bounding box coordinates {"x": 0, "y": 0, "width": 100, "height": 20}'
    )
    
    # Verification / 校驗
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_extractions'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['receipt', 'field_name']
        verbose_name = 'Field Extraction / 欄位提取'
        verbose_name_plural = 'Field Extractions / 欄位提取'
        unique_together = ['receipt', 'field_name']
    
    def __str__(self):
        return f"{self.receipt.id} - {self.field_name}: {self.extracted_value[:50]}"
    
    @property
    def final_value(self):
        """Return corrected value if available, otherwise extracted value"""
        return self.corrected_value if self.corrected_value else self.extracted_value
    
    @property
    def needs_review(self):
        """Flag if confidence is low and not verified"""
        return self.confidence < 0.8 and not self.is_verified


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
    # Brainstorming Meeting
    MeetingStatus,
    BrainstormMeeting,
    MeetingParticipantRole,
    MeetingParticipantStatus,
    BrainstormMeetingParticipant,
    # AI Agent System
    AIActionType,
    AIActionStatus,
    AIAgent,
    AIActionLog,
    AIConversation,
)