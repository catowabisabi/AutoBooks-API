from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserSettings, SubscriptionPlan, UserSubscription


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Fields to display in the user list
    list_display = ['email', 'full_name', 'role', 'employee_type', 'is_active', 'is_staff']

    # Fields that can be clicked to view user details
    list_display_links = ['email', 'full_name']

    # Fields that can be filtered in the sidebar
    list_filter = ['role', 'employee_type', 'is_active', 'is_staff', 'created_at']

    # Fields that can be searched
    search_fields = ['email', 'full_name']

    # Fields that are read-only
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_login']

    # Order by email
    ordering = ['email']

    # Fieldsets for the user detail/edit page
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Personal Info', {
            'fields': ('full_name', 'role', 'employee_type')
        }),
        ('Employment Info', {
            'fields': ('designation', 'department', 'manager')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at')
        }),
    )

    # Fieldsets for adding a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'role'),
        }),
    )


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'subscription_plan', 'subscription_status']
    list_filter = ['subscription_plan', 'subscription_status']
    search_fields = ['user__email']


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price_monthly', 'price_yearly', 'is_active', 'is_popular', 'sort_order']
    list_filter = ['plan_type', 'is_active', 'is_popular']
    list_editable = ['is_active', 'is_popular', 'sort_order']
    search_fields = ['name', 'name_en', 'name_zh']
    ordering = ['sort_order']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('plan_type', 'name', 'name_en', 'name_zh', 'description', 'description_en', 'description_zh')
        }),
        ('Pricing', {
            'fields': ('price_monthly', 'price_yearly', 'currency')
        }),
        ('Limits', {
            'fields': ('max_users', 'max_companies', 'max_storage_gb', 'max_documents', 
                      'max_invoices_monthly', 'max_employees', 'max_projects')
        }),
        ('Features', {
            'fields': ('has_ai_assistant', 'has_advanced_analytics', 'has_custom_reports', 
                      'has_api_access', 'has_priority_support', 'has_sso', 
                      'has_audit_logs', 'has_data_export', 'has_multi_currency', 'has_custom_branding')
        }),
        ('AI Limits', {
            'fields': ('ai_queries_monthly', 'rag_documents')
        }),
        ('Status', {
            'fields': ('is_active', 'is_popular', 'sort_order')
        }),
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'billing_cycle', 'start_date', 'end_date', 'next_billing_date']
    list_filter = ['status', 'billing_cycle', 'plan']
    search_fields = ['user__email', 'plan__name']
    raw_id_fields = ['user', 'plan']
    date_hierarchy = 'start_date'
