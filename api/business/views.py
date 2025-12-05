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
    Revenue, BMIIPOPRRecord, BMIDocument
)
from .serializers import (
    CompanySerializer, CompanyListSerializer,
    AuditProjectSerializer, AuditProjectListSerializer,
    TaxReturnCaseSerializer, TaxReturnCaseListSerializer,
    BillableHourSerializer, BillableHourListSerializer,
    RevenueSerializer, RevenueListSerializer,
    BMIIPOPRRecordSerializer, BMIIPOPRRecordListSerializer,
    BMIDocumentSerializer, OverviewStatsSerializer
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


class DashboardOverviewView(APIView):
    """
    Get dashboard overview statistics
    GET /api/v1/business/dashboard/
    """
    permission_classes = get_permission_classes()
    
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
