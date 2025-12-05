"""
Analytics Module URL Configuration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DashboardViewSet,
    ChartViewSet,
    AnalyticsSalesViewSet,
    KPIMetricViewSet,
    ReportScheduleViewSet,
    AnalyticsDashboardView,
)

router = DefaultRouter()
router.register(r'dashboards', DashboardViewSet, basename='dashboard')
router.register(r'charts', ChartViewSet, basename='chart')
router.register(r'sales', AnalyticsSalesViewSet, basename='analytics-sales')
router.register(r'kpis', KPIMetricViewSet, basename='kpi')
router.register(r'report-schedules', ReportScheduleViewSet, basename='report-schedule')

urlpatterns = [
    path('', include(router.urls)),
    path('overview/', AnalyticsDashboardView.as_view(), name='analytics-overview'),
]

