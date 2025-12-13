"""
HRMS Module URL Configuration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DepartmentViewSet,
    DesignationViewSet,
    EmployeeViewSet,
    LeaveApplicationViewSet,
    LeaveBalanceViewSet,
    PayrollPeriodViewSet,
    PayrollViewSet,
    ProjectViewSet,
    TaskViewSet,
    UserProjectMappingViewSet,
    HRMSDashboardView,
)

router = DefaultRouter()
router.include_root_view = False  # Disable API root view to avoid "api" tag
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'designations', DesignationViewSet, basename='designation')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'leave-applications', LeaveApplicationViewSet, basename='leave-application')
router.register(r'leave-balances', LeaveBalanceViewSet, basename='leave-balance')
router.register(r'payroll-periods', PayrollPeriodViewSet, basename='payroll-period')
router.register(r'payrolls', PayrollViewSet, basename='payroll')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'project-mappings', UserProjectMappingViewSet, basename='project-mapping')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', HRMSDashboardView.as_view(), name='hrms-dashboard'),
]

