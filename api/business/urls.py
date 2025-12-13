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
    # New Financial PR & IPO Advisory ViewSets
    ListedClientViewSet,
    AnnouncementViewSet,
    MediaCoverageViewSet,
    IPOMandateViewSet,
    ServiceRevenueViewSet,
    ActiveEngagementViewSet,
    ClientPerformanceViewSet,
    ClientIndustryViewSet,
    MediaSentimentRecordViewSet,
    RevenueTrendViewSet,
    # IPO and Partner ViewSets
    IPOTimelineProgressViewSet,
    IPODealFunnelViewSet,
    IPODealSizeViewSet,
    BusinessPartnerViewSet,
)

router = DefaultRouter()
router.include_root_view = False  # Disable API root view to avoid "api" tag
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'audits', AuditProjectViewSet, basename='audit')
router.register(r'tax-returns', TaxReturnCaseViewSet, basename='tax-return')
router.register(r'billable-hours', BillableHourViewSet, basename='billable-hour')
router.register(r'revenues', RevenueViewSet, basename='revenue')
router.register(r'bmi-projects', BMIIPOPRRecordViewSet, basename='bmi-project')
router.register(r'bmi-documents', BMIDocumentViewSet, basename='bmi-document')

# Financial PR & IPO Advisory endpoints
router.register(r'listed-clients', ListedClientViewSet, basename='listed-client')
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'media-coverage', MediaCoverageViewSet, basename='media-coverage')
router.register(r'ipo-mandates', IPOMandateViewSet, basename='ipo-mandate')
router.register(r'service-revenues', ServiceRevenueViewSet, basename='service-revenue')
router.register(r'engagements', ActiveEngagementViewSet, basename='engagement')
router.register(r'client-performance', ClientPerformanceViewSet, basename='client-performance')
router.register(r'client-industries', ClientIndustryViewSet, basename='client-industry')
router.register(r'media-sentiment', MediaSentimentRecordViewSet, basename='media-sentiment')
router.register(r'revenue-trends', RevenueTrendViewSet, basename='revenue-trend')

# IPO and Partner endpoints
router.register(r'ipo-timeline-progress', IPOTimelineProgressViewSet, basename='ipo-timeline-progress')
router.register(r'ipo-deal-funnel', IPODealFunnelViewSet, basename='ipo-deal-funnel')
router.register(r'ipo-deal-size', IPODealSizeViewSet, basename='ipo-deal-size')
router.register(r'partners', BusinessPartnerViewSet, basename='partner')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardOverviewView.as_view(), name='business-dashboard'),
]
