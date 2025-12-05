"""
AI Assistants Extended Models
=============================
Email Assistant, Planner AI, Document Assistant, Brainstorming Assistant
"""

import uuid
from enum import Enum
from decimal import Decimal
from django.db import models
from django.conf import settings
from core.models import BaseModel


# =================================================================
# Email Assistant Models
# =================================================================

class EmailStatus(models.TextChoices):
    """Email status"""
    DRAFT = 'DRAFT', 'Draft'
    SENT = 'SENT', 'Sent'
    RECEIVED = 'RECEIVED', 'Received'
    ARCHIVED = 'ARCHIVED', 'Archived'
    DELETED = 'DELETED', 'Deleted'


class EmailCategory(models.TextChoices):
    """Email category types"""
    PAYMENT_REMINDER = 'PAYMENT_REMINDER', 'Payment Reminder'
    PROJECT_FOLLOWUP = 'PROJECT_FOLLOWUP', 'Project Follow-up'
    TAX_DOC_REQUEST = 'TAX_DOC_REQUEST', 'Tax Document Request'
    MEETING_CONFIRM = 'MEETING_CONFIRM', 'Meeting Confirmation'
    INVOICE_SENT = 'INVOICE_SENT', 'Invoice Sent'
    EVENT_INVITE = 'EVENT_INVITE', 'Event Invitation'
    IPO_RELEASE = 'IPO_RELEASE', 'IPO Release'
    BILLING_ISSUE = 'BILLING_ISSUE', 'Billing Issue'
    DOCUMENT_MISSING = 'DOCUMENT_MISSING', 'Document Missing'
    APPRECIATION = 'APPRECIATION', 'Appreciation Email'
    GENERAL = 'GENERAL', 'General'


class EmailPriority(models.TextChoices):
    """Email priority levels"""
    LOW = 'LOW', 'Low'
    NORMAL = 'NORMAL', 'Normal'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'


class EmailAccount(BaseModel):
    """
    Email account configuration (per company/user)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_accounts'
    )
    
    # Account info
    email_address = models.EmailField()
    display_name = models.CharField(max_length=255, blank=True)
    
    # SMTP Settings (encrypted in production)
    smtp_host = models.CharField(max_length=255, blank=True)
    smtp_port = models.IntegerField(default=587)
    smtp_user = models.CharField(max_length=255, blank=True)
    smtp_password = models.CharField(max_length=255, blank=True)  # Should be encrypted
    use_tls = models.BooleanField(default=True)
    
    # IMAP Settings for receiving
    imap_host = models.CharField(max_length=255, blank=True)
    imap_port = models.IntegerField(default=993)
    
    # Demo mode
    is_demo = models.BooleanField(default=True, help_text='Use demo mailbox instead of real SMTP')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Account'
        verbose_name_plural = 'Email Accounts'
    
    def __str__(self):
        return f"{self.display_name or self.email_address}"


class Email(BaseModel):
    """
    Email message model for AI Email Assistant
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Account
    account = models.ForeignKey(
        EmailAccount,
        on_delete=models.CASCADE,
        related_name='emails',
        null=True,
        blank=True
    )
    
    # Email headers
    from_address = models.EmailField()
    from_name = models.CharField(max_length=255, blank=True)
    to_addresses = models.JSONField(default=list, help_text='List of recipient emails')
    cc_addresses = models.JSONField(default=list, blank=True)
    bcc_addresses = models.JSONField(default=list, blank=True)
    reply_to = models.EmailField(blank=True)
    
    # Content
    subject = models.CharField(max_length=500)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    
    # Metadata
    status = models.CharField(
        max_length=20,
        choices=EmailStatus.choices,
        default=EmailStatus.RECEIVED
    )
    category = models.CharField(
        max_length=30,
        choices=EmailCategory.choices,
        default=EmailCategory.GENERAL
    )
    priority = models.CharField(
        max_length=20,
        choices=EmailPriority.choices,
        default=EmailPriority.NORMAL
    )
    
    # Threading
    thread_id = models.CharField(max_length=255, blank=True, db_index=True)
    in_reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    # Dates
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Flags
    is_read = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    is_spam = models.BooleanField(default=False)
    has_attachments = models.BooleanField(default=False)
    
    # AI Analysis
    ai_summary = models.TextField(blank=True, help_text='AI generated summary')
    ai_sentiment = models.CharField(max_length=20, blank=True)
    ai_action_items = models.JSONField(default=list, help_text='Extracted action items')
    ai_suggested_reply = models.TextField(blank=True)
    ai_keywords = models.JSONField(default=list)
    
    # Links to other modules
    related_project = models.ForeignKey(
        'business.AuditProject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emails'
    )
    related_client = models.ForeignKey(
        'business.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emails'
    )
    
    class Meta:
        ordering = ['-received_at', '-created_at']
        verbose_name = 'Email'
        verbose_name_plural = 'Emails'
    
    def __str__(self):
        return f"{self.subject} - {self.from_address}"


class EmailAttachment(BaseModel):
    """Email attachments"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name='attachments')
    
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to='email_attachments/%Y/%m/')
    content_type = models.CharField(max_length=100, blank=True)
    size = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['filename']


class EmailTemplate(BaseModel):
    """Reusable email templates"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=255)
    category = models.CharField(
        max_length=30,
        choices=EmailCategory.choices,
        default=EmailCategory.GENERAL
    )
    subject_template = models.CharField(max_length=500)
    body_template = models.TextField()
    variables = models.JSONField(default=list, help_text='Template variables like {{client_name}}')
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_templates'
    )
    is_shared = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['category', 'name']


# =================================================================
# Planner AI Models
# =================================================================

class TaskPriority(models.TextChoices):
    """Task priority levels (can be AI-adjusted)"""
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class TaskStatus(models.TextChoices):
    """Task status"""
    TODO = 'TODO', 'To Do'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    BLOCKED = 'BLOCKED', 'Blocked'
    DONE = 'DONE', 'Done'
    CANCELLED = 'CANCELLED', 'Cancelled'


class PlannerTask(BaseModel):
    """
    AI-managed tasks for Planner
    AI can create, modify, reprioritize tasks
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic info
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    
    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planner_tasks'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_planner_tasks'
    )
    
    # Status & Priority
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO
    )
    priority = models.CharField(
        max_length=20,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM
    )
    
    # Dates
    due_date = models.DateField(null=True, blank=True)
    due_time = models.TimeField(null=True, blank=True)
    reminder_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # AI Management
    ai_generated = models.BooleanField(default=False, help_text='Was this task created by AI?')
    ai_priority_score = models.FloatField(default=0, help_text='AI calculated priority score 0-100')
    ai_suggested_deadline = models.DateField(null=True, blank=True)
    ai_reasoning = models.TextField(blank=True, help_text='AI explanation for priority/deadline')
    
    # Source tracking
    source_type = models.CharField(
        max_length=30,
        blank=True,
        help_text='email, campaign, meeting, manual'
    )
    source_id = models.CharField(max_length=100, blank=True)
    
    # Related entities
    related_project = models.ForeignKey(
        'business.AuditProject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planner_tasks'
    )
    related_client = models.ForeignKey(
        'business.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planner_tasks'
    )
    related_email = models.ForeignKey(
        Email,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planner_tasks'
    )
    
    # Tags
    tags = models.JSONField(default=list)
    
    class Meta:
        ordering = ['-ai_priority_score', 'due_date', '-created_at']
        verbose_name = 'Planner Task'
        verbose_name_plural = 'Planner Tasks'
    
    def __str__(self):
        return f"{self.title} ({self.status})"


class ScheduleEvent(BaseModel):
    """Calendar events for Planner"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=500, blank=True)
    
    # Participants
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organized_events'
    )
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='attending_events',
        blank=True
    )
    
    # Time
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_all_day = models.BooleanField(default=False)
    timezone = models.CharField(max_length=50, default='Asia/Hong_Kong')
    
    # Recurrence
    is_recurring = models.BooleanField(default=False)
    recurrence_rule = models.CharField(max_length=255, blank=True)
    
    # Meeting details
    meeting_link = models.URLField(blank=True)
    meeting_type = models.CharField(max_length=30, blank=True)  # zoom, teams, in-person
    
    # AI Integration
    ai_generated = models.BooleanField(default=False)
    source_email = models.ForeignKey(
        Email,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedule_events'
    )
    
    class Meta:
        ordering = ['start_time']


# =================================================================
# Document Assistant Models
# =================================================================

class DocumentType(models.TextChoices):
    """Document types"""
    INVOICE = 'INVOICE', 'Invoice'
    CONTRACT = 'CONTRACT', 'Contract'
    PROPOSAL = 'PROPOSAL', 'Proposal'
    REPORT = 'REPORT', 'Report'
    MEETING_MINUTES = 'MEETING_MINUTES', 'Meeting Minutes'
    PR_RELEASE = 'PR_RELEASE', 'Press Release'
    FINANCIAL = 'FINANCIAL', 'Financial Document'
    LEGAL = 'LEGAL', 'Legal Document'
    OTHER = 'OTHER', 'Other'


class AIDocument(BaseModel):
    """
    Document model for AI Document Assistant
    Supports OCR, summarization, comparison
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic info
    title = models.CharField(max_length=500)
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.OTHER
    )
    
    # File
    file = models.FileField(upload_to='ai_documents/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True)
    
    # Ownership
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_documents'
    )
    
    # OCR & Text extraction
    is_ocr_processed = models.BooleanField(default=False)
    extracted_text = models.TextField(blank=True)
    ocr_confidence = models.FloatField(default=0)
    
    # AI Analysis
    ai_summary = models.TextField(blank=True)
    ai_keywords = models.JSONField(default=list)
    ai_entities = models.JSONField(default=dict, help_text='Named entities: dates, amounts, names')
    ai_sentiment = models.CharField(max_length=20, blank=True)
    
    # Searchable
    search_vector = models.TextField(blank=True, help_text='Full text search content')
    
    # Relations
    related_project = models.ForeignKey(
        'business.AuditProject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_documents'
    )
    related_client = models.ForeignKey(
        'business.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_documents'
    )
    related_campaign = models.ForeignKey(
        'business.BMIIPOPRRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_documents'
    )
    
    # Tags
    tags = models.JSONField(default=list)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI Document'
        verbose_name_plural = 'AI Documents'
    
    def __str__(self):
        return f"{self.title} ({self.document_type})"


class DocumentComparison(BaseModel):
    """Compare two document versions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    document_a = models.ForeignKey(
        AIDocument,
        on_delete=models.CASCADE,
        related_name='comparisons_as_a'
    )
    document_b = models.ForeignKey(
        AIDocument,
        on_delete=models.CASCADE,
        related_name='comparisons_as_b'
    )
    
    # Results
    similarity_score = models.FloatField(default=0)
    differences = models.JSONField(default=list)
    ai_analysis = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_comparisons'
    )
    
    class Meta:
        ordering = ['-created_at']


# =================================================================
# Brainstorming Assistant Models
# =================================================================

class BrainstormSession(BaseModel):
    """
    AI Brainstorming session
    For generating ideas, campaign breakdowns, pitch writing
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Session info
    title = models.CharField(max_length=500)
    session_type = models.CharField(
        max_length=30,
        choices=[
            ('IDEA_GENERATOR', 'Idea Generator'),
            ('CAMPAIGN_BREAKDOWN', 'Campaign Breakdown'),
            ('MARKET_ANALYSIS', 'Market Analysis'),
            ('PITCH_WRITER', 'Pitch Writer'),
            ('STRATEGY', 'Strategy Planning'),
            ('GENERAL', 'General Brainstorm'),
        ],
        default='GENERAL'
    )
    
    # Input
    prompt = models.TextField(help_text='User input/question')
    context = models.JSONField(default=dict, help_text='Additional context for AI')
    
    # Output
    ai_response = models.TextField(blank=True)
    ai_structured_output = models.JSONField(default=dict)
    
    # Saved items
    saved_ideas = models.JSONField(default=list)
    
    # Owner
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='brainstorm_sessions'
    )
    
    # Link to project/campaign
    related_campaign = models.ForeignKey(
        'business.BMIIPOPRRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='brainstorm_sessions'
    )
    related_client = models.ForeignKey(
        'business.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='brainstorm_sessions'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Brainstorm Session'
        verbose_name_plural = 'Brainstorm Sessions'
    
    def __str__(self):
        return f"{self.title} ({self.session_type})"


class BrainstormIdea(BaseModel):
    """Individual idea from a brainstorm session"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    session = models.ForeignKey(
        BrainstormSession,
        on_delete=models.CASCADE,
        related_name='ideas'
    )
    
    content = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    is_selected = models.BooleanField(default=False)
    rating = models.IntegerField(default=0, help_text='User rating 1-5')
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-rating', '-created_at']
