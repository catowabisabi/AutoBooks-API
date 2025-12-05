from django.contrib import admin
from .models import (
    Company, AuditProject, TaxReturnCase, BillableHour, 
    Revenue, BMIIPOPRRecord, BMIDocument
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'industry', 'contact_person', 'contact_email', 'created_at']
    list_filter = ['industry', 'is_active']
    search_fields = ['name', 'registration_number', 'tax_id', 'contact_person']


@admin.register(AuditProject)
class AuditProjectAdmin(admin.ModelAdmin):
    list_display = ['company', 'fiscal_year', 'audit_type', 'status', 'progress', 'deadline', 'assigned_to']
    list_filter = ['status', 'audit_type', 'fiscal_year']
    search_fields = ['company__name', 'notes']
    autocomplete_fields = ['company', 'assigned_to']


@admin.register(TaxReturnCase)
class TaxReturnCaseAdmin(admin.ModelAdmin):
    list_display = ['company', 'tax_year', 'tax_type', 'status', 'progress', 'deadline', 'handler']
    list_filter = ['status', 'tax_type', 'tax_year', 'documents_received']
    search_fields = ['company__name']
    autocomplete_fields = ['company', 'handler']


@admin.register(BillableHour)
class BillableHourAdmin(admin.ModelAdmin):
    list_display = ['employee', 'company', 'role', 'date', 'actual_hours', 'total_cost', 'is_billable', 'is_invoiced']
    list_filter = ['role', 'is_billable', 'is_invoiced', 'date']
    search_fields = ['employee__email', 'employee__full_name', 'company__name', 'description']
    date_hierarchy = 'date'


@admin.register(Revenue)
class RevenueAdmin(admin.ModelAdmin):
    list_display = ['company', 'invoice_number', 'total_amount', 'received_amount', 'pending_amount', 'status', 'due_date']
    list_filter = ['status', 'invoice_date', 'due_date']
    search_fields = ['company__name', 'invoice_number', 'contact_name']
    date_hierarchy = 'invoice_date'


@admin.register(BMIIPOPRRecord)
class BMIIPOPRRecordAdmin(admin.ModelAdmin):
    list_display = ['project_name', 'company', 'project_type', 'stage', 'status', 'progress', 'estimated_value']
    list_filter = ['project_type', 'stage', 'status']
    search_fields = ['project_name', 'company__name']
    autocomplete_fields = ['company', 'lead_manager']


@admin.register(BMIDocument)
class BMIDocumentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'bmi_project', 'file_type', 'uploaded_by', 'created_at']
    list_filter = ['file_type']
    search_fields = ['file_name', 'bmi_project__project_name']
