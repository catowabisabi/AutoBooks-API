"""
Business Module Serializers
===========================
Serializers for Companies, Audits, Tax Returns, Billable Hours, Revenue, and BMI IPO/PR.
"""

from rest_framework import serializers
from .models import (
    Company, AuditProject, TaxReturnCase, BillableHour, 
    Revenue, BMIIPOPRRecord, BMIDocument
)
from users.serializers import UserSerializer


class CompanySerializer(serializers.ModelSerializer):
    """Serializer for Company model"""
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'registration_number', 'tax_id', 'address',
            'industry', 'contact_person', 'contact_email', 'contact_phone',
            'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompanyListSerializer(serializers.ModelSerializer):
    """Light serializer for list views"""
    
    class Meta:
        model = Company
        fields = ['id', 'name', 'industry', 'contact_person', 'is_active']


class AuditProjectSerializer(serializers.ModelSerializer):
    """Serializer for AuditProject model"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    
    class Meta:
        model = AuditProject
        fields = [
            'id', 'company', 'company_name', 'fiscal_year', 'audit_type',
            'progress', 'status', 'start_date', 'deadline', 'completion_date',
            'assigned_to', 'assigned_to_name', 'budget_hours', 'actual_hours',
            'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AuditProjectListSerializer(serializers.ModelSerializer):
    """Light serializer for list views"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    
    class Meta:
        model = AuditProject
        fields = [
            'id', 'company_name', 'fiscal_year', 'audit_type',
            'progress', 'status', 'deadline', 'assigned_to_name'
        ]


class TaxReturnCaseSerializer(serializers.ModelSerializer):
    """Serializer for TaxReturnCase model"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    handler_name = serializers.CharField(source='handler.full_name', read_only=True)
    
    class Meta:
        model = TaxReturnCase
        fields = [
            'id', 'company', 'company_name', 'tax_year', 'tax_type',
            'progress', 'status', 'deadline', 'submitted_date',
            'handler', 'handler_name', 'tax_amount', 'documents_received',
            'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaxReturnCaseListSerializer(serializers.ModelSerializer):
    """Light serializer for list views"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    handler_name = serializers.CharField(source='handler.full_name', read_only=True)
    
    class Meta:
        model = TaxReturnCase
        fields = [
            'id', 'company_name', 'tax_year', 'tax_type', 'progress',
            'status', 'deadline', 'handler_name', 'documents_received'
        ]


class BillableHourSerializer(serializers.ModelSerializer):
    """Serializer for BillableHour model"""
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    effective_rate = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_cost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = BillableHour
        fields = [
            'id', 'employee', 'employee_name', 'company', 'company_name',
            'project_reference', 'role', 'base_hourly_rate', 'hourly_rate_multiplier',
            'effective_rate', 'date', 'actual_hours', 'total_cost',
            'description', 'is_billable', 'is_invoiced',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'effective_rate', 'total_cost']


class BillableHourListSerializer(serializers.ModelSerializer):
    """Light serializer for list views"""
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    total_cost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = BillableHour
        fields = [
            'id', 'employee_name', 'company_name', 'role', 'date',
            'actual_hours', 'total_cost', 'is_billable'
        ]


class RevenueSerializer(serializers.ModelSerializer):
    """Serializer for Revenue model"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    pending_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    is_fully_paid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Revenue
        fields = [
            'id', 'company', 'company_name', 'invoice_number', 'description',
            'total_amount', 'received_amount', 'pending_amount', 'is_fully_paid',
            'status', 'invoice_date', 'due_date', 'received_date',
            'contact_name', 'contact_email', 'contact_phone',
            'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'pending_amount', 'is_fully_paid']


class RevenueListSerializer(serializers.ModelSerializer):
    """Light serializer for list views"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    pending_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = Revenue
        fields = [
            'id', 'company_name', 'invoice_number', 'total_amount',
            'received_amount', 'pending_amount', 'status', 'due_date'
        ]


class BMIDocumentSerializer(serializers.ModelSerializer):
    """Serializer for BMIDocument model"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    
    class Meta:
        model = BMIDocument
        fields = [
            'id', 'bmi_project', 'file_name', 'file_path', 'file_type',
            'file_size', 'uploaded_by', 'uploaded_by_name', 'description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BMIIPOPRRecordSerializer(serializers.ModelSerializer):
    """Serializer for BMIIPOPRRecord model"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    lead_manager_name = serializers.CharField(source='lead_manager.full_name', read_only=True)
    documents = BMIDocumentSerializer(many=True, read_only=True)
    
    class Meta:
        model = BMIIPOPRRecord
        fields = [
            'id', 'project_name', 'company', 'company_name',
            'stage', 'status', 'project_type',
            'estimated_value', 'total_cost',
            'start_date', 'target_completion_date', 'actual_completion_date',
            'progress', 'lead_manager', 'lead_manager_name',
            'documents', 'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BMIIPOPRRecordListSerializer(serializers.ModelSerializer):
    """Light serializer for list views"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    lead_manager_name = serializers.CharField(source='lead_manager.full_name', read_only=True)
    
    class Meta:
        model = BMIIPOPRRecord
        fields = [
            'id', 'project_name', 'company_name', 'project_type',
            'stage', 'status', 'progress', 'lead_manager_name'
        ]


# Summary/Dashboard Serializers
class OverviewStatsSerializer(serializers.Serializer):
    """Serializer for dashboard overview stats"""
    total_audits = serializers.IntegerField()
    audits_in_progress = serializers.IntegerField()
    total_tax_returns = serializers.IntegerField()
    tax_returns_pending = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_billable_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    bmi_projects_active = serializers.IntegerField()
