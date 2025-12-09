"""
HRMS Module Serializers
=======================
Serializers for Employees, Departments, Designations, Leaves, and Payroll.
"""

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import (
    Department, Designation, Employee, LeaveApplication, LeaveBalance,
    PayrollPeriod, Payroll, PayrollItem, Project, Task, UserProjectMapping
)


class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ['id', 'name', 'description', 'level', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DepartmentSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(source='manager.full_name', read_only=True)
    sub_departments_count = serializers.SerializerMethodField()
    employees_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'description', 'code', 'parent', 'manager', 'manager_name',
            'budget', 'sub_departments_count', 'employees_count',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    @extend_schema_field(serializers.IntegerField())
    def get_sub_departments_count(self, obj):
        return obj.sub_departments.count()
    
    @extend_schema_field(serializers.IntegerField())
    def get_employees_count(self, obj):
        return obj.employees.count()


class DepartmentListSerializer(serializers.ModelSerializer):
    employees_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'employees_count', 'is_active']
    
    @extend_schema_field(serializers.IntegerField())
    def get_employees_count(self, obj):
        return obj.employees.count()


class EmployeeSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    manager_name = serializers.CharField(source='manager.user.full_name', read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'user_email', 'user_full_name', 'employee_id',
            'department', 'department_name', 'designation', 'designation_name',
            'manager', 'manager_name',
            'employment_status', 'employment_type',
            'hire_date', 'probation_end_date', 'termination_date',
            'date_of_birth', 'gender', 'nationality', 'id_number',
            'phone', 'personal_email', 'address',
            'emergency_contact_name', 'emergency_contact_phone',
            'base_salary', 'payment_frequency', 'bank_name', 'bank_account',
            'annual_leave_balance', 'sick_leave_balance',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeListSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'user_full_name', 'user_email',
            'department_name', 'designation_name',
            'employment_status', 'employment_type', 'hire_date'
        ]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_id_code = serializers.CharField(source='employee.employee_id', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.full_name', read_only=True)
    
    class Meta:
        model = LeaveApplication
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_code',
            'leave_type', 'start_date', 'end_date', 'total_days',
            'reason', 'status', 'approved_by', 'approved_by_name', 'approved_at',
            'rejection_reason', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'approved_at']


class LeaveApplicationListSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    
    class Meta:
        model = LeaveApplication
        fields = [
            'id', 'employee_name', 'leave_type', 'start_date', 'end_date',
            'total_days', 'status'
        ]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    remaining_days = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)
    
    class Meta:
        model = LeaveBalance
        fields = [
            'id', 'employee', 'employee_name', 'year', 'leave_type',
            'entitled_days', 'used_days', 'carried_over', 'remaining_days',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'remaining_days']


class PayrollPeriodSerializer(serializers.ModelSerializer):
    payroll_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PayrollPeriod
        fields = [
            'id', 'name', 'year', 'month', 'start_date', 'end_date',
            'payment_date', 'status', 'payroll_count', 'notes',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    @extend_schema_field(serializers.IntegerField())
    def get_payroll_count(self, obj):
        return obj.payroll_records.count()


class PayrollItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollItem
        fields = ['id', 'payroll', 'item_type', 'name', 'description', 'amount']


class PayrollSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_id_code = serializers.CharField(source='employee.employee_id', read_only=True)
    period_name = serializers.CharField(source='period.name', read_only=True)
    gross_pay = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_deductions = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net_pay = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    items = PayrollItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Payroll
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_code',
            'period', 'period_name', 'status',
            'basic_salary', 'overtime_pay', 'allowances', 'bonus', 'commission', 'other_earnings',
            'tax_deduction', 'mpf_employee', 'mpf_employer', 'insurance_deduction',
            'loan_deduction', 'other_deductions',
            'working_days', 'absent_days', 'overtime_hours',
            'gross_pay', 'total_deductions', 'net_pay',
            'payment_date', 'payment_reference', 'items', 'notes',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'gross_pay', 'total_deductions', 'net_pay']


class PayrollListSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_id_code = serializers.CharField(source='employee.employee_id', read_only=True)
    period_name = serializers.CharField(source='period.name', read_only=True)
    net_pay = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Payroll
        fields = [
            'id', 'employee_id_code', 'employee_name', 'period_name',
            'basic_salary', 'net_pay', 'status'
        ]


class ProjectSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    tasks_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'start_date', 'end_date',
            'status', 'owner', 'owner_name', 'budget', 'progress',
            'tasks_count', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    @extend_schema_field(serializers.IntegerField())
    def get_tasks_count(self, obj):
        return obj.tasks.count()


class ProjectListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    
    class Meta:
        model = Project
        fields = ['id', 'name', 'status', 'progress', 'owner_name', 'end_date']


class TaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.full_name', read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'project', 'project_name', 'title', 'description',
            'due_date', 'status', 'priority',
            'assigned_to', 'assigned_to_name', 'assigned_by', 'assigned_by_name',
            'estimated_hours', 'actual_hours',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaskListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'project_name', 'status', 'priority',
            'due_date', 'assigned_to_name'
        ]


class UserProjectMappingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = UserProjectMapping
        fields = ['id', 'user', 'user_name', 'project', 'project_name', 'role', 'is_active']

