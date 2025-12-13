"""
Analytics Module Views
======================
ViewSets for Dashboards, Charts, Sales Analytics, and KPIs.
"""

from decimal import Decimal
from django.conf import settings
from django.db.models import Sum, Avg, Count
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import Dashboard, Chart, AnalyticsSales, KPIMetric, ReportSchedule
from .serializers import (
    DashboardSerializer, DashboardListSerializer,
    ChartSerializer, ChartListSerializer,
    AnalyticsSalesSerializer, AnalyticsSalesListSerializer,
    KPIMetricSerializer, KPIMetricListSerializer,
    ReportScheduleSerializer
)
from core.schema_serializers import AnalyticsDashboardResponseSerializer
from .schema import (
    DashboardViewSetSchema, ChartViewSetSchema, AnalyticsSalesViewSetSchema,
    KPIMetricViewSetSchema, ReportScheduleViewSetSchema, AnalyticsDashboardViewSchema
)


# Allow anonymous access in DEBUG mode for development
def get_permission_classes():
    if settings.DEBUG:
        return [AllowAny]
    return [IsAuthenticated]


@DashboardViewSetSchema
class DashboardViewSet(viewsets.ModelViewSet):
    """ViewSet for Dashboards"""
    queryset = Dashboard.objects.prefetch_related('charts').all()
    permission_classes = get_permission_classes()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'title']
    ordering = ['-is_default', '-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DashboardListSerializer
        return DashboardSerializer
    
    @action(detail=False, methods=['get'])
    def default(self, request):
        """Get the default dashboard"""
        dashboard = Dashboard.objects.filter(is_default=True).first()
        if dashboard:
            return Response(DashboardSerializer(dashboard).data)
        return Response({'error': 'No default dashboard'}, status=status.HTTP_404_NOT_FOUND)


@ChartViewSetSchema
class ChartViewSet(viewsets.ModelViewSet):
    """ViewSet for Charts"""
    queryset = Chart.objects.select_related('dashboard').all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['dashboard', 'type']
    search_fields = ['title']
    ordering_fields = ['position', 'created_at']
    ordering = ['position']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChartListSerializer
        return ChartSerializer


@AnalyticsSalesViewSetSchema
class AnalyticsSalesViewSet(viewsets.ModelViewSet):
    """ViewSet for Sales Analytics"""
    queryset = AnalyticsSales.objects.all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['year', 'month']
    ordering_fields = ['year', 'month']
    ordering = ['-year', '-month']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AnalyticsSalesListSerializer
        return AnalyticsSalesSerializer
    
    @action(detail=False, methods=['get'])
    def yearly_summary(self, request):
        """Get yearly sales summary"""
        year = request.query_params.get('year')
        qs = self.get_queryset()
        if year:
            qs = qs.filter(year=year)
        
        summary = qs.aggregate(
            total_revenue=Sum('revenue'),
            avg_growth=Avg('growth_percentage'),
            total_new_clients=Sum('new_clients'),
            avg_churn=Avg('churn_rate'),
            total_deals=Sum('deals_closed'),
        )
        
        return Response({
            'year': year,
            **{k: str(v) if v else '0' for k, v in summary.items()},
            'monthly_data': AnalyticsSalesListSerializer(qs.order_by('month'), many=True).data
        })
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get sales trends data for charts"""
        qs = self.get_queryset().order_by('year', 'month')[:12]
        return Response({
            'labels': [f"{s.year}-{s.month:02d}" for s in qs],
            'revenue': [str(s.revenue) for s in qs],
            'growth': [str(s.growth_percentage) for s in qs],
            'clients': [s.total_clients for s in qs],
        })


@KPIMetricViewSetSchema
class KPIMetricViewSet(viewsets.ModelViewSet):
    """ViewSet for KPI Metrics"""
    queryset = KPIMetric.objects.all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'period']
    search_fields = ['name', 'description']
    ordering_fields = ['category', 'name']
    ordering = ['category', 'name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return KPIMetricListSerializer
        return KPIMetricSerializer
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get KPIs grouped by category"""
        categories = KPIMetric.objects.values('category').distinct()
        result = {}
        for cat in categories:
            category = cat['category']
            result[category] = KPIMetricListSerializer(
                KPIMetric.objects.filter(category=category),
                many=True
            ).data
        return Response(result)
    
    @action(detail=True, methods=['post'])
    def update_value(self, request, pk=None):
        """Update KPI current value"""
        kpi = self.get_object()
        new_value = request.data.get('value')
        if new_value is None:
            return Response({'error': 'Value required'}, status=status.HTTP_400_BAD_REQUEST)
        
        kpi.previous_value = kpi.current_value
        kpi.current_value = Decimal(str(new_value))
        
        # Update trend
        if kpi.current_value > kpi.previous_value:
            kpi.trend = 'UP'
        elif kpi.current_value < kpi.previous_value:
            kpi.trend = 'DOWN'
        else:
            kpi.trend = 'NEUTRAL'
        
        kpi.save()
        return Response(KPIMetricSerializer(kpi).data)


@ReportScheduleViewSetSchema
class ReportScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet for Report Schedules"""
    queryset = ReportSchedule.objects.all()
    serializer_class = ReportScheduleSerializer
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['report_type', 'frequency', 'is_active']
    search_fields = ['name']


# Analytics Dashboard Overview
@AnalyticsDashboardViewSchema
class AnalyticsDashboardView(APIView):
    """
    Get analytics dashboard overview
    GET /api/v1/analytics/overview/
    """
    permission_classes = get_permission_classes()
    serializer_class = AnalyticsDashboardResponseSerializer
    
    def get(self, request):
        from django.utils import timezone
        current_year = timezone.now().year
        current_month = timezone.now().month
        
        # Get current month data
        current_sales = AnalyticsSales.objects.filter(
            year=current_year, month=current_month
        ).first()
        
        # Get previous month for comparison
        prev_month = current_month - 1 if current_month > 1 else 12
        prev_year = current_year if current_month > 1 else current_year - 1
        prev_sales = AnalyticsSales.objects.filter(
            year=prev_year, month=prev_month
        ).first()
        
        # Get YTD totals
        ytd = AnalyticsSales.objects.filter(year=current_year).aggregate(
            total_revenue=Sum('revenue'),
            total_new_clients=Sum('new_clients'),
            total_deals=Sum('deals_closed'),
        )
        
        # Get KPIs
        kpis = KPIMetric.objects.filter(is_active=True)[:10]
        
        return Response({
            'current_month': AnalyticsSalesSerializer(current_sales).data if current_sales else None,
            'previous_month': AnalyticsSalesSerializer(prev_sales).data if prev_sales else None,
            'ytd': {
                'total_revenue': str(ytd['total_revenue'] or 0),
                'total_new_clients': ytd['total_new_clients'] or 0,
                'total_deals': ytd['total_deals'] or 0,
            },
            'kpis': KPIMetricListSerializer(kpis, many=True).data,
            'monthly_trend': AnalyticsSalesListSerializer(
                AnalyticsSales.objects.filter(year=current_year).order_by('month'),
                many=True
            ).data
        })

