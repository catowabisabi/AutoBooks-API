from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


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
