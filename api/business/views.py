"""
Business Module Views
=====================
ViewSets for Companies, Audits, Tax Returns, Billable Hours, Revenue, and BMI IPO/PR.
"""

from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.conf import settings
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Company, AuditProject, TaxReturnCase, BillableHour, 
    Revenue, BMIIPOPRRecord, BMIDocument,
    ListedClient, Announcement, MediaCoverage, IPOMandate,
    ServiceRevenue, ActiveEngagement, ClientPerformance,
    ClientIndustry, MediaSentimentRecord, RevenueTrend,
    IPOTimelineProgress, IPODealFunnel, IPODealSize, BusinessPartner
)
from .serializers import (
    CompanySerializer, CompanyListSerializer,
    AuditProjectSerializer, AuditProjectListSerializer,
    TaxReturnCaseSerializer, TaxReturnCaseListSerializer,
    BillableHourSerializer, BillableHourListSerializer,
    RevenueSerializer, RevenueListSerializer,
    BMIIPOPRRecordSerializer, BMIIPOPRRecordListSerializer,
    BMIDocumentSerializer, OverviewStatsSerializer,
    IPOTimelineProgressSerializer, IPOTimelineProgressListSerializer,
    IPODealFunnelSerializer, IPODealFunnelListSerializer,
    IPODealSizeSerializer, IPODealSizeListSerializer,
    BusinessPartnerSerializer, BusinessPartnerListSerializer
)


# Allow anonymous access in DEBUG mode for development
def get_permission_classes():
    if settings.DEBUG:
        return [AllowAny]
    return [IsAuthenticated]


class CompanyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Company CRUD operations
    
    list: GET /api/v1/business/companies/
    create: POST /api/v1/business/companies/
    retrieve: GET /api/v1/business/companies/{id}/
    update: PUT /api/v1/business/companies/{id}/
    partial_update: PATCH /api/v1/business/companies/{id}/
    destroy: DELETE /api/v1/business/companies/{id}/
    """
    queryset = Company.objects.all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['industry', 'is_active']
    search_fields = ['name', 'registration_number', 'contact_person']
    ordering_fields = ['name', 'created_at', 'industry']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CompanyListSerializer
        return CompanySerializer
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get company statistics"""
        total = Company.objects.count()
        by_industry = Company.objects.values('industry').annotate(count=Count('id'))
        return Response({
            'total': total,
            'by_industry': list(by_industry),
        })


class AuditProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AuditProject CRUD operations
    
    list: GET /api/v1/business/audits/
    create: POST /api/v1/business/audits/
    retrieve: GET /api/v1/business/audits/{id}/
    update: PUT /api/v1/business/audits/{id}/
    partial_update: PATCH /api/v1/business/audits/{id}/
    destroy: DELETE /api/v1/business/audits/{id}/
    """
    queryset = AuditProject.objects.select_related('company', 'assigned_to').all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'audit_type', 'fiscal_year', 'assigned_to']
    search_fields = ['company__name', 'notes']
    ordering_fields = ['deadline', 'progress', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AuditProjectListSerializer
        return AuditProjectSerializer
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get audit summary statistics"""
        qs = self.get_queryset()
        return Response({
            'total': qs.count(),
            'by_status': list(qs.values('status').annotate(count=Count('id'))),
            'avg_progress': qs.aggregate(avg=Sum('progress') / Count('id'))['avg'] or 0,
            'overdue': qs.filter(deadline__lt=timezone.now().date(), status__in=['NOT_STARTED', 'PLANNING', 'FIELDWORK', 'REVIEW']).count(),
        })


class TaxReturnCaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for TaxReturnCase CRUD operations
    """
    queryset = TaxReturnCase.objects.select_related('company', 'handler').all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'tax_type', 'tax_year', 'handler', 'documents_received']
    search_fields = ['company__name', 'notes']
    ordering_fields = ['deadline', 'progress', 'created_at']
    ordering = ['deadline']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TaxReturnCaseListSerializer
        return TaxReturnCaseSerializer
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get tax return summary statistics"""
        qs = self.get_queryset()
        from django.utils import timezone
        return Response({
            'total': qs.count(),
            'by_status': list(qs.values('status').annotate(count=Count('id'))),
            'pending_documents': qs.filter(documents_received=False).count(),
            'upcoming_deadlines': qs.filter(
                deadline__lte=timezone.now().date() + timezone.timedelta(days=30),
                status__in=['PENDING', 'IN_PROGRESS']
            ).count(),
        })


class BillableHourViewSet(viewsets.ModelViewSet):
    """
    ViewSet for BillableHour CRUD operations
    """
    queryset = BillableHour.objects.select_related('employee', 'company').all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_billable', 'is_invoiced', 'company', 'employee']
    search_fields = ['employee__full_name', 'company__name', 'description']
    ordering_fields = ['date', 'actual_hours', 'created_at']
    ordering = ['-date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BillableHourListSerializer
        return BillableHourSerializer
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get billable hours summary"""
        qs = self.get_queryset()
        
        # Calculate total costs manually
        total_billable = Decimal('0')
        for bh in qs.filter(is_billable=True):
            total_billable += bh.total_cost
        
        return Response({
            'total_hours': qs.aggregate(total=Sum('actual_hours'))['total'] or 0,
            'billable_hours': qs.filter(is_billable=True).aggregate(total=Sum('actual_hours'))['total'] or 0,
            'total_billable_value': str(total_billable),
            'by_role': list(qs.values('role').annotate(
                hours=Sum('actual_hours'),
                count=Count('id')
            )),
        })
    
    @action(detail=False, methods=['get'])
    def by_employee(self, request):
        """Get hours grouped by employee"""
        qs = self.get_queryset()
        result = qs.values(
            'employee__id', 'employee__full_name', 'role'
        ).annotate(
            total_hours=Sum('actual_hours'),
            entries=Count('id')
        ).order_by('-total_hours')
        return Response(list(result))


class RevenueViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Revenue CRUD operations
    """
    queryset = Revenue.objects.select_related('company').all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'company']
    search_fields = ['company__name', 'invoice_number', 'contact_name']
    ordering_fields = ['due_date', 'total_amount', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RevenueListSerializer
        return RevenueSerializer
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get revenue summary statistics"""
        qs = self.get_queryset()
        totals = qs.aggregate(
            total=Sum('total_amount'),
            received=Sum('received_amount'),
        )
        pending = (totals['total'] or Decimal('0')) - (totals['received'] or Decimal('0'))
        
        return Response({
            'total_revenue': str(totals['total'] or 0),
            'received_amount': str(totals['received'] or 0),
            'pending_amount': str(pending),
            'by_status': list(qs.values('status').annotate(
                count=Count('id'),
                total=Sum('total_amount')
            )),
        })
    
    @action(detail=True, methods=['post'])
    def record_payment(self, request, pk=None):
        """Record a payment for a revenue entry"""
        revenue = self.get_object()
        amount = Decimal(request.data.get('amount', '0'))
        
        if amount <= 0:
            return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        
        revenue.received_amount += amount
        if revenue.received_amount >= revenue.total_amount:
            revenue.status = 'RECEIVED'
            from django.utils import timezone
            revenue.received_date = timezone.now().date()
        elif revenue.received_amount > 0:
            revenue.status = 'PARTIAL'
        
        revenue.save()
        return Response(RevenueSerializer(revenue).data)


class BMIIPOPRRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for BMIIPOPRRecord CRUD operations
    """
    queryset = BMIIPOPRRecord.objects.select_related('company', 'lead_manager').prefetch_related('documents').all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['stage', 'status', 'project_type', 'lead_manager']
    search_fields = ['project_name', 'company__name', 'notes']
    ordering_fields = ['progress', 'target_completion_date', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BMIIPOPRRecordListSerializer
        return BMIIPOPRRecordSerializer
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get BMI project summary"""
        qs = self.get_queryset()
        return Response({
            'total': qs.count(),
            'by_stage': list(qs.values('stage').annotate(count=Count('id'))),
            'by_status': list(qs.values('status').annotate(count=Count('id'))),
            'total_value': str(qs.aggregate(total=Sum('estimated_value'))['total'] or 0),
        })


class BMIDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for BMI Documents"""
    queryset = BMIDocument.objects.select_related('bmi_project', 'uploaded_by').all()
    serializer_class = BMIDocumentSerializer
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['bmi_project', 'file_type']


# Dashboard Overview View
from django.utils import timezone
from core.schema_serializers import DashboardOverviewResponseSerializer


class DashboardOverviewView(APIView):
    """
    Get dashboard overview statistics
    GET /api/v1/business/dashboard/
    """
    permission_classes = get_permission_classes()
    serializer_class = DashboardOverviewResponseSerializer
    
    def get(self, request):
        # Audit stats
        audits = AuditProject.objects.all()
        total_audits = audits.count()
        audits_in_progress = audits.filter(status__in=['PLANNING', 'FIELDWORK', 'REVIEW', 'REPORTING']).count()
        
        # Tax return stats
        tax_returns = TaxReturnCase.objects.all()
        total_tax_returns = tax_returns.count()
        tax_returns_pending = tax_returns.filter(status__in=['PENDING', 'IN_PROGRESS']).count()
        
        # Revenue stats
        revenues = Revenue.objects.all()
        revenue_totals = revenues.aggregate(
            total=Sum('total_amount'),
            received=Sum('received_amount')
        )
        total_revenue = revenue_totals['total'] or Decimal('0')
        received_revenue = revenue_totals['received'] or Decimal('0')
        pending_revenue = total_revenue - received_revenue
        
        # Billable hours
        billable_hours = BillableHour.objects.filter(is_billable=True)
        total_billable_hours = billable_hours.aggregate(total=Sum('actual_hours'))['total'] or Decimal('0')
        
        # BMI projects
        bmi_active = BMIIPOPRRecord.objects.filter(status__in=['ACTIVE', 'ON_TRACK']).count()
        
        return Response({
            'total_audits': total_audits,
            'audits_in_progress': audits_in_progress,
            'total_tax_returns': total_tax_returns,
            'tax_returns_pending': tax_returns_pending,
            'total_revenue': str(total_revenue),
            'pending_revenue': str(pending_revenue),
            'total_billable_hours': str(total_billable_hours),
            'bmi_projects_active': bmi_active,
            
            # Recent items
            'recent_audits': AuditProjectListSerializer(
                audits.order_by('-updated_at')[:5], many=True
            ).data,
            'recent_tax_returns': TaxReturnCaseListSerializer(
                tax_returns.order_by('-updated_at')[:5], many=True
            ).data,
            'recent_revenues': RevenueListSerializer(
                revenues.order_by('-created_at')[:5], many=True
            ).data,
        })


# =================================================================
# Financial PR & IPO Advisory ViewSets
# =================================================================

from .models import (
    ListedClient, Announcement, MediaCoverage, IPOMandate,
    ServiceRevenue, ActiveEngagement, ClientPerformance,
    ClientIndustry, MediaSentimentRecord, RevenueTrend
)
from .serializers import (
    ListedClientSerializer, ListedClientListSerializer,
    AnnouncementSerializer, AnnouncementListSerializer,
    MediaCoverageSerializer, MediaCoverageListSerializer,
    IPOMandateSerializer, IPOMandateListSerializer,
    ServiceRevenueSerializer, ServiceRevenueListSerializer,
    ActiveEngagementSerializer, ActiveEngagementListSerializer,
    ClientPerformanceSerializer, ClientPerformanceListSerializer,
    ClientIndustrySerializer, MediaSentimentRecordSerializer,
    RevenueTrendSerializer
)


class ListedClientViewSet(viewsets.ModelViewSet):
    """ViewSet for ListedClient CRUD operations"""
    queryset = ListedClient.objects.select_related('company').all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'exchange', 'sector']
    search_fields = ['company__name', 'stock_code', 'primary_contact']
    ordering_fields = ['stock_code', 'market_cap', 'annual_retainer', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ListedClientListSerializer
        return ListedClientSerializer
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get listed clients summary"""
        qs = self.get_queryset()
        return Response({
            'total': qs.count(),
            'active': qs.filter(status='ACTIVE').count(),
            'by_exchange': list(qs.values('exchange').annotate(count=Count('id'))),
            'by_sector': list(qs.values('sector').annotate(count=Count('id'))),
            'total_retainer': str(qs.aggregate(total=Sum('annual_retainer'))['total'] or 0),
        })


class AnnouncementViewSet(viewsets.ModelViewSet):
    """ViewSet for Announcement CRUD operations"""
    queryset = Announcement.objects.select_related('listed_client__company', 'handler').all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['announcement_type', 'status', 'listed_client', 'handler']
    search_fields = ['title', 'listed_client__company__name', 'listed_client__stock_code']
    ordering_fields = ['publish_date', 'deadline', 'created_at']
    ordering = ['-publish_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AnnouncementListSerializer
        return AnnouncementSerializer
    
    @action(detail=False, methods=['get'])
    def this_month(self, request):
        """Get announcements for this month"""
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        qs = self.get_queryset().filter(
            publish_date__gte=start_of_month,
            publish_date__lte=today
        )
        return Response({
            'count': qs.count(),
            'by_type': list(qs.values('announcement_type').annotate(count=Count('id'))),
            'announcements': AnnouncementListSerializer(qs[:10], many=True).data
        })


class MediaCoverageViewSet(viewsets.ModelViewSet):
    """ViewSet for MediaCoverage CRUD operations"""
    queryset = MediaCoverage.objects.select_related('listed_client__company', 'company').all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['sentiment', 'is_press_release', 'listed_client', 'company']
    search_fields = ['title', 'media_outlet', 'listed_client__company__name']
    ordering_fields = ['publish_date', 'reach', 'engagement', 'created_at']
    ordering = ['-publish_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MediaCoverageListSerializer
        return MediaCoverageSerializer
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get media coverage summary"""
        qs = self.get_queryset()
        return Response({
            'total': qs.count(),
            'by_sentiment': list(qs.values('sentiment').annotate(count=Count('id'))),
            'total_reach': qs.aggregate(total=Sum('reach'))['total'] or 0,
            'total_engagement': qs.aggregate(total=Sum('engagement'))['total'] or 0,
        })


class IPOMandateViewSet(viewsets.ModelViewSet):
    """ViewSet for IPOMandate CRUD operations"""
    queryset = IPOMandate.objects.select_related('company', 'lead_partner').all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['stage', 'target_exchange', 'deal_size_category', 'is_sfc_approved', 'lead_partner']
    search_fields = ['project_name', 'company__name']
    ordering_fields = ['deal_size', 'probability', 'target_listing_date', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return IPOMandateListSerializer
        return IPOMandateSerializer
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get IPO mandate summary"""
        qs = self.get_queryset()
        total_pipeline = qs.aggregate(total=Sum('deal_size'))['total'] or Decimal('0')
        total_fees = qs.aggregate(total=Sum('estimated_fee'))['total'] or Decimal('0')
        
        # SFC stats
        sfc_submitted = qs.filter(sfc_application_date__isnull=False).count()
        sfc_approved = qs.filter(is_sfc_approved=True).count()
        sfc_rate = (sfc_approved / sfc_submitted * 100) if sfc_submitted > 0 else 0
        
        return Response({
            'total': qs.count(),
            'active': qs.exclude(stage__in=['LISTING', 'POST_IPO', 'WITHDRAWN']).count(),
            'by_stage': list(qs.values('stage').annotate(count=Count('id'))),
            'by_deal_size': list(qs.values('deal_size_category').annotate(count=Count('id'))),
            'total_pipeline_value': str(total_pipeline),
            'total_estimated_fees': str(total_fees),
            'sfc_approval_rate': round(sfc_rate, 1),
        })
    
    @action(detail=False, methods=['get'])
    def deal_funnel(self, request):
        """Get deal funnel data"""
        qs = self.get_queryset()
        stages = [
            'INITIAL_CONTACT', 'PITCH', 'MANDATE_WON', 'PREPARATION',
            'A1_FILING', 'HKEX_REVIEW', 'SFC_REVIEW', 'HEARING',
            'ROADSHOW', 'LISTING'
        ]
        funnel = []
        for stage in stages:
            count = qs.filter(stage=stage).count()
            value = qs.filter(stage=stage).aggregate(total=Sum('deal_size'))['total'] or 0
            funnel.append({
                'stage': stage,
                'count': count,
                'value': str(value)
            })
        return Response(funnel)


class ServiceRevenueViewSet(viewsets.ModelViewSet):
    """ViewSet for ServiceRevenue CRUD operations"""
    queryset = ServiceRevenue.objects.select_related('company').all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['service_type', 'period_year', 'period_month', 'company']
    search_fields = ['company__name']
    ordering_fields = ['period_year', 'period_month', 'amount', 'created_at']
    ordering = ['-period_year', '-period_month']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceRevenueListSerializer
        return ServiceRevenueSerializer
    
    @action(detail=False, methods=['get'])
    def by_service(self, request):
        """Get revenue breakdown by service type"""
        year = request.query_params.get('year', timezone.now().year)
        qs = self.get_queryset().filter(period_year=year)
        return Response(list(
            qs.values('service_type').annotate(
                total_amount=Sum('amount'),
                total_hours=Sum('billable_hours')
            ).order_by('-total_amount')
        ))


class ActiveEngagementViewSet(viewsets.ModelViewSet):
    """ViewSet for ActiveEngagement CRUD operations"""
    queryset = ActiveEngagement.objects.select_related('company', 'lead').all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['engagement_type', 'status', 'company', 'lead']
    search_fields = ['title', 'company__name']
    ordering_fields = ['start_date', 'value', 'progress', 'created_at']
    ordering = ['-start_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ActiveEngagementListSerializer
        return ActiveEngagementSerializer
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get active engagements summary"""
        qs = self.get_queryset()
        active = qs.filter(status='ACTIVE')
        return Response({
            'total': qs.count(),
            'active_count': active.count(),
            'total_value': str(active.aggregate(total=Sum('value'))['total'] or 0),
            'by_type': list(active.values('engagement_type').annotate(count=Count('id'))),
            'avg_progress': active.aggregate(avg=Sum('progress') / Count('id'))['avg'] or 0,
        })


class ClientPerformanceViewSet(viewsets.ModelViewSet):
    """ViewSet for ClientPerformance CRUD operations"""
    queryset = ClientPerformance.objects.select_related('company').all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['period_year', 'period_quarter', 'company']
    search_fields = ['company__name']
    ordering_fields = ['period_year', 'period_quarter', 'revenue_generated', 'satisfaction_score']
    ordering = ['-period_year', '-period_quarter']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ClientPerformanceListSerializer
        return ClientPerformanceSerializer


class ClientIndustryViewSet(viewsets.ModelViewSet):
    """ViewSet for ClientIndustry CRUD operations"""
    queryset = ClientIndustry.objects.all()
    serializer_class = ClientIndustrySerializer
    permission_classes = get_permission_classes()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'client_count', 'total_revenue']
    ordering = ['name']


class MediaSentimentRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for MediaSentimentRecord CRUD operations"""
    queryset = MediaSentimentRecord.objects.all()
    serializer_class = MediaSentimentRecordSerializer
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['period_date']
    ordering_fields = ['period_date', 'sentiment_score']
    ordering = ['-period_date']
    
    @action(detail=False, methods=['get'])
    def trend(self, request):
        """Get sentiment trend over time"""
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=days)
        qs = self.get_queryset().filter(
            period_date__gte=start_date,
            period_date__lte=end_date
        ).order_by('period_date')
        return Response(MediaSentimentRecordSerializer(qs, many=True).data)


class RevenueTrendViewSet(viewsets.ModelViewSet):
    """ViewSet for RevenueTrend CRUD operations"""
    queryset = RevenueTrend.objects.all()
    serializer_class = RevenueTrendSerializer
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['period_year', 'period_month']
    ordering_fields = ['period_year', 'period_month', 'total_revenue']
    ordering = ['-period_year', '-period_month']
    
    @action(detail=False, methods=['get'])
    def yearly(self, request):
        """Get yearly revenue summary"""
        qs = self.get_queryset()
        return Response(list(
            qs.values('period_year').annotate(
                total=Sum('total_revenue'),
                recurring=Sum('recurring_revenue'),
                project=Sum('project_revenue'),
                new_clients=Sum('new_clients'),
                churned=Sum('churned_clients')
            ).order_by('-period_year')
        ))


# =================================================================
# IPO Timeline Progress ViewSet
# =================================================================

class IPOTimelineProgressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for IPO Timeline Progress CRUD operations
    
    Tracks completion percentage of each IPO phase:
    - Due Diligence
    - Documentation  
    - Regulatory Filing
    - Marketing
    - Pricing
    """
    queryset = IPOTimelineProgress.objects.all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['company', 'phase', 'status']
    search_fields = ['company__name', 'phase']
    ordering_fields = ['phase', 'progress_percentage', 'target_date', 'created_at']
    ordering = ['phase']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return IPOTimelineProgressListSerializer
        return IPOTimelineProgressSerializer
    
    @action(detail=False, methods=['get'])
    def by_company(self, request):
        """Get IPO timeline progress grouped by company"""
        company_id = request.query_params.get('company_id')
        if company_id:
            qs = self.get_queryset().filter(company_id=company_id)
        else:
            qs = self.get_queryset()
        return Response(IPOTimelineProgressSerializer(qs, many=True).data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary of all phases with average completion"""
        from django.db.models import Avg
        qs = self.get_queryset().values('phase').annotate(
            avg_progress=Avg('progress_percentage'),
            total_count=Count('id')
        ).order_by('phase')
        return Response(list(qs))


# =================================================================
# IPO Deal Funnel ViewSet
# =================================================================

class IPODealFunnelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for IPO Deal Funnel CRUD operations
    
    Tracks deal conversion through stages:
    - Leads
    - Qualified
    - Proposal
    - Negotiation
    - Closed Won
    """
    queryset = IPODealFunnel.objects.all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['company', 'stage', 'period_date']
    search_fields = ['company__name', 'stage']
    ordering_fields = ['stage', 'deal_count', 'conversion_rate', 'period_date']
    ordering = ['-period_date', 'stage']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return IPODealFunnelListSerializer
        return IPODealFunnelSerializer
    
    @action(detail=False, methods=['get'])
    def current_funnel(self, request):
        """Get current month's funnel data"""
        from django.utils import timezone
        current_date = timezone.now().date()
        qs = self.get_queryset().filter(
            period_date__year=current_date.year,
            period_date__month=current_date.month
        )
        return Response(IPODealFunnelSerializer(qs, many=True).data)
    
    @action(detail=False, methods=['get'])
    def conversion_rates(self, request):
        """Get conversion rates by stage"""
        from django.db.models import Avg
        qs = self.get_queryset().values('stage').annotate(
            avg_conversion=Avg('conversion_rate'),
            total_deals=Sum('deal_count')
        ).order_by('stage')
        return Response(list(qs))


# =================================================================
# IPO Deal Size ViewSet
# =================================================================

class IPODealSizeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for IPO Deal Size CRUD operations
    
    Tracks deal distribution by size:
    - Mega (>$1B)
    - Large ($500M-1B)
    - Mid ($100M-500M)
    - Small (<$100M)
    """
    queryset = IPODealSize.objects.all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['company', 'size_category', 'period_date']
    search_fields = ['company__name', 'size_category']
    ordering_fields = ['size_category', 'deal_count', 'total_amount', 'period_date']
    ordering = ['-period_date', 'size_category']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return IPODealSizeListSerializer
        return IPODealSizeSerializer
    
    @action(detail=False, methods=['get'])
    def distribution(self, request):
        """Get current deal size distribution"""
        qs = self.get_queryset().values('size_category').annotate(
            total_deals=Sum('deal_count'),
            total_value=Sum('total_amount')
        ).order_by('size_category')
        return Response(list(qs))
    
    @action(detail=False, methods=['get'])
    def trend(self, request):
        """Get deal size distribution trend over time"""
        months = int(request.query_params.get('months', 6))
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta
        end_date = timezone.now().date()
        start_date = end_date - relativedelta(months=months)
        qs = self.get_queryset().filter(
            period_date__gte=start_date,
            period_date__lte=end_date
        ).order_by('period_date', 'size_category')
        return Response(IPODealSizeSerializer(qs, many=True).data)


# =================================================================
# Business Partner ViewSet
# =================================================================

class BusinessPartnerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Business Partner CRUD operations
    
    Manages all partner types:
    - KOL (Key Opinion Leaders)
    - Provider (Service Providers)
    - Vendor (Suppliers)
    - Media (Media Partners)
    - Consultant (External Consultants)
    """
    queryset = BusinessPartner.objects.all()
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['company', 'partner_type', 'status']
    search_fields = ['name', 'contact_person', 'contact_email', 'service_description']
    ordering_fields = ['name', 'partner_type', 'status', 'contract_value', 'rating', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BusinessPartnerListSerializer
        return BusinessPartnerSerializer
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get partners grouped by type"""
        partner_type = request.query_params.get('type')
        if partner_type:
            qs = self.get_queryset().filter(partner_type=partner_type)
        else:
            qs = self.get_queryset()
        return Response(BusinessPartnerSerializer(qs, many=True).data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active partners"""
        qs = self.get_queryset().filter(status='active', is_active=True)
        return Response(BusinessPartnerSerializer(qs, many=True).data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get partner summary by type"""
        qs = self.get_queryset().filter(is_active=True).values('partner_type').annotate(
            total_count=Count('id'),
            active_count=Count('id', filter=Q(status='active')),
            total_value=Sum('contract_value')
        ).order_by('partner_type')
        return Response(list(qs))
