from django.contrib import admin
from ai_assistants.models import (
    Receipt, ReceiptComparison, ExpenseReport,
    EmailAccount, Email, EmailAttachment, EmailTemplate,
    PlannerTask, ScheduleEvent,
    AIDocument, DocumentComparison,
    BrainstormSession, BrainstormIdea,
)


# Receipt models
@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['id', 'uploaded_by', 'vendor_name', 'status', 'total_amount', 'category', 'created_at']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['vendor_name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ExpenseReport)
class ExpenseReportAdmin(admin.ModelAdmin):
    list_display = ['report_number', 'title', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['report_number', 'title']


# Email Assistant models
@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    list_display = ['email_address', 'display_name', 'is_demo', 'is_active', 'created_at']
    list_filter = ['is_demo', 'is_active']
    search_fields = ['email_address', 'display_name']


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ['subject', 'from_address', 'category', 'status', 'is_read', 'received_at']
    list_filter = ['status', 'category', 'priority', 'is_read', 'is_starred']
    search_fields = ['subject', 'from_address', 'body_text']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_shared', 'created_at']
    list_filter = ['category', 'is_shared']
    search_fields = ['name', 'subject_template']


# Planner models
@admin.register(PlannerTask)
class PlannerTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'priority', 'due_date', 'ai_generated', 'ai_priority_score']
    list_filter = ['status', 'priority', 'ai_generated']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ScheduleEvent)
class ScheduleEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_time', 'end_time', 'meeting_type', 'ai_generated']
    list_filter = ['meeting_type', 'is_recurring', 'ai_generated']
    search_fields = ['title', 'description']


# Document models
@admin.register(AIDocument)
class AIDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'original_filename', 'is_ocr_processed', 'created_at']
    list_filter = ['document_type', 'is_ocr_processed']
    search_fields = ['title', 'extracted_text', 'ai_summary']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(DocumentComparison)
class DocumentComparisonAdmin(admin.ModelAdmin):
    list_display = ['id', 'document_a', 'document_b', 'similarity_score', 'created_at']
    readonly_fields = ['id', 'created_at']


# Brainstorm models
@admin.register(BrainstormSession)
class BrainstormSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'session_type', 'created_by', 'created_at']
    list_filter = ['session_type']
    search_fields = ['title', 'prompt', 'ai_response']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(BrainstormIdea)
class BrainstormIdeaAdmin(admin.ModelAdmin):
    list_display = ['content', 'session', 'category', 'rating', 'is_selected']
    list_filter = ['is_selected', 'category']
    search_fields = ['content']
