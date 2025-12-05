"""
Business Module URL Configuration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompanyViewSet,
    AuditProjectViewSet,
    TaxReturnCaseViewSet,
    BillableHourViewSet,
    RevenueViewSet,
    BMIIPOPRRecordViewSet,
    BMIDocumentViewSet,
    DashboardOverviewView,
)

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'audits', AuditProjectViewSet, basename='audit')
router.register(r'tax-returns', TaxReturnCaseViewSet, basename='tax-return')
router.register(r'billable-hours', BillableHourViewSet, basename='billable-hour')
router.register(r'revenues', RevenueViewSet, basename='revenue')
router.register(r'bmi-projects', BMIIPOPRRecordViewSet, basename='bmi-project')
router.register(r'bmi-documents', BMIDocumentViewSet, basename='bmi-document')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardOverviewView.as_view(), name='business-dashboard'),
]
