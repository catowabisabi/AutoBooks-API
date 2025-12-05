"""
HRMS Module Views
=================
ViewSets for Employees, Departments, Designations, Leaves, and Payroll.
"""

from decimal import Decimal
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .serializers import (
    DesignationSerializer, DepartmentSerializer, DepartmentListSerializer,
    EmployeeSerializer, EmployeeListSerializer,
    LeaveApplicationSerializer, LeaveApplicationListSerializer, LeaveBalanceSerializer,
    PayrollPeriodSerializer, PayrollSerializer, PayrollListSerializer, PayrollItemSerializer,
    ProjectSerializer, ProjectListSerializer, TaskSerializer, TaskListSerializer,
    UserProjectMappingSerializer
)
from .models import (
    Designation, Department, Employee, LeaveApplication, LeaveBalance,
    LeaveTypes, LeaveStatus, PayrollPeriod, Payroll, PayrollItem, PayrollStatus,
    Project, ProjectStatuses, Task, TaskStatuses, TaskPriority, UserProjectMapping
)


class DesignationViewSet(viewsets.ModelViewSet):
    """ViewSet for Designations (Job Titles)"""
    queryset = Designation.objects.all()
    serializer_class = DesignationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['level', 'name']
    ordering = ['level']


class DepartmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Departments"""
    queryset = Department.objects.select_related('manager', 'parent').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'parent']
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DepartmentListSerializer
        return DepartmentSerializer
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get department hierarchy as tree"""
        root_depts = Department.objects.filter(parent__isnull=True, is_active=True)
        
        def build_tree(dept):
            return {
                'id': str(dept.id),
                'name': dept.name,
                'code': dept.code,
                'children': [build_tree(child) for child in dept.sub_departments.filter(is_active=True)]
            }
        
        return Response([build_tree(d) for d in root_depts])


class EmployeeViewSet(viewsets.ModelViewSet):
    """ViewSet for Employees"""
    queryset = Employee.objects.select_related('user', 'department', 'designation', 'manager').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'designation', 'employment_status', 'employment_type']
    search_fields = ['employee_id', 'user__full_name', 'user__email']
    ordering_fields = ['employee_id', 'hire_date', 'created_at']
    ordering = ['employee_id']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EmployeeListSerializer
        return EmployeeSerializer
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get employee summary statistics"""
        qs = self.get_queryset()
        return Response({
            'total': qs.count(),
            'active': qs.filter(employment_status='ACTIVE').count(),
            'by_department': list(qs.values('department__name').annotate(count=Count('id'))),
            'by_type': list(qs.values('employment_type').annotate(count=Count('id'))),
            'by_status': list(qs.values('employment_status').annotate(count=Count('id'))),
        })
    
    @action(detail=True, methods=['get'])
    def leave_balances(self, request, pk=None):
        """Get leave balances for an employee"""
        employee = self.get_object()
        balances = LeaveBalance.objects.filter(employee=employee, year=timezone.now().year)
        return Response(LeaveBalanceSerializer(balances, many=True).data)
    
    @action(detail=True, methods=['get'])
    def payroll_history(self, request, pk=None):
        """Get payroll history for an employee"""
        employee = self.get_object()
        payrolls = Payroll.objects.filter(employee=employee).order_by('-period__year', '-period__month')[:12]
        return Response(PayrollListSerializer(payrolls, many=True).data)


class LeaveApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for Leave Applications"""
    queryset = LeaveApplication.objects.select_related('employee__user', 'approved_by__user').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'leave_type', 'status']
    search_fields = ['employee__user__full_name', 'reason']
    ordering_fields = ['start_date', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LeaveApplicationListSerializer
        return LeaveApplicationSerializer
    
    @action(detail=False, methods=['get'])
    def leave_types(self, request):
        """Returns available leave types"""
        return Response({
            'leave_types': [{'value': lt.value, 'label': lt.value.replace('_', ' ').title()} for lt in LeaveTypes]
        })
    
    @action(detail=False, methods=['get'])
    def leave_statuses(self, request):
        """Returns available leave statuses"""
        return Response({
            'leave_statuses': [{'value': ls.value, 'label': ls.value.title()} for ls in LeaveStatus]
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a leave application"""
        leave = self.get_object()
        if leave.status != 'PENDING':
            return Response({'error': 'Can only approve pending applications'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get approver employee (assuming current user has employee profile)
        try:
            approver = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            approver = None
        
        leave.status = 'APPROVED'
        leave.approved_by = approver
        leave.approved_at = timezone.now()
        leave.save()
        
        return Response(LeaveApplicationSerializer(leave).data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a leave application"""
        leave = self.get_object()
        if leave.status != 'PENDING':
            return Response({'error': 'Can only reject pending applications'}, status=status.HTTP_400_BAD_REQUEST)
        
        leave.status = 'REJECTED'
        leave.rejection_reason = request.data.get('reason', '')
        leave.save()
        
        return Response(LeaveApplicationSerializer(leave).data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get leave summary statistics"""
        qs = self.get_queryset()
        current_year = timezone.now().year
        return Response({
            'total': qs.filter(start_date__year=current_year).count(),
            'pending': qs.filter(status='PENDING').count(),
            'by_type': list(qs.filter(start_date__year=current_year).values('leave_type').annotate(
                count=Count('id'),
                total_days=Sum('total_days')
            )),
        })


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    """ViewSet for Leave Balances"""
    queryset = LeaveBalance.objects.select_related('employee__user').all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'year', 'leave_type']


class PayrollPeriodViewSet(viewsets.ModelViewSet):
    """ViewSet for Payroll Periods"""
    queryset = PayrollPeriod.objects.all()
    serializer_class = PayrollPeriodSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['year', 'status']
    ordering_fields = ['year', 'month']
    ordering = ['-year', '-month']
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current payroll period"""
        today = timezone.now().date()
        period = PayrollPeriod.objects.filter(
            start_date__lte=today,
            end_date__gte=today
        ).first()
        if period:
            return Response(PayrollPeriodSerializer(period).data)
        return Response({'error': 'No current period found'}, status=status.HTTP_404_NOT_FOUND)


class PayrollViewSet(viewsets.ModelViewSet):
    """ViewSet for Payroll Records"""
    queryset = Payroll.objects.select_related('employee__user', 'period').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'period', 'status']
    search_fields = ['employee__user__full_name', 'employee__employee_id']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PayrollListSerializer
        return PayrollSerializer
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get payroll summary for a period"""
        period_id = request.query_params.get('period')
        qs = self.get_queryset()
        if period_id:
            qs = qs.filter(period_id=period_id)
        
        # Calculate totals manually to get accurate sums
        total_gross = Decimal('0')
        total_deductions = Decimal('0')
        total_net = Decimal('0')
        for p in qs:
            total_gross += p.gross_pay
            total_deductions += p.total_deductions
            total_net += p.net_pay
        
        return Response({
            'total_records': qs.count(),
            'total_gross_pay': str(total_gross),
            'total_deductions': str(total_deductions),
            'total_net_pay': str(total_net),
            'by_status': list(qs.values('status').annotate(count=Count('id'))),
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a payroll record"""
        payroll = self.get_object()
        if payroll.status not in ['DRAFT', 'PENDING_APPROVAL']:
            return Response({'error': 'Cannot approve this payroll'}, status=status.HTTP_400_BAD_REQUEST)
        payroll.status = 'APPROVED'
        payroll.save()
        return Response(PayrollSerializer(payroll).data)


class ProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for Projects"""
    queryset = Project.objects.select_related('owner').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'owner']
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'end_date', 'progress']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        return ProjectSerializer
    
    @action(detail=False, methods=['get'])
    def project_statuses(self, request):
        """Returns available project statuses"""
        return Response({
            'project_statuses': [{'value': ps.value, 'label': ps.value.replace('_', ' ').title()} for ps in ProjectStatuses]
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get project summary"""
        qs = self.get_queryset()
        return Response({
            'total': qs.count(),
            'by_status': list(qs.values('status').annotate(count=Count('id'))),
            'avg_progress': qs.aggregate(avg=Avg('progress'))['avg'] or 0,
        })
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update project progress"""
        project = self.get_object()
        progress = request.data.get('progress', 0)
        if not 0 <= progress <= 100:
            return Response({'error': 'Progress must be between 0 and 100'}, status=status.HTTP_400_BAD_REQUEST)
        project.progress = progress
        if progress == 100:
            project.status = 'COMPLETED'
        project.save()
        return Response(ProjectSerializer(project).data)


class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet for Tasks"""
    queryset = Task.objects.select_related('project', 'assigned_to', 'assigned_by').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'status', 'priority', 'assigned_to']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'priority', 'created_at']
    ordering = ['-priority', 'due_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        return TaskSerializer
    
    @action(detail=False, methods=['get'])
    def task_statuses(self, request):
        """Returns available task statuses"""
        return Response({
            'task_statuses': [{'value': ts.value, 'label': ts.value.replace('_', ' ').title()} for ts in TaskStatuses]
        })
    
    @action(detail=False, methods=['get'])
    def task_priorities(self, request):
        """Returns available task priorities"""
        return Response({
            'task_priorities': [{'value': tp.value, 'label': tp.value.title()} for tp in TaskPriority]
        })
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update task status"""
        task = self.get_object()
        new_status = request.data.get('status')
        if new_status not in [ts.value for ts in TaskStatuses]:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        task.status = new_status
        task.save()
        return Response(TaskSerializer(task).data)
    
    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        """Get tasks assigned to current user"""
        tasks = self.get_queryset().filter(assigned_to=request.user)
        return Response(TaskListSerializer(tasks, many=True).data)


class UserProjectMappingViewSet(viewsets.ModelViewSet):
    """ViewSet for User-Project Mappings"""
    queryset = UserProjectMapping.objects.select_related('user', 'project').all()
    serializer_class = UserProjectMappingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'project', 'is_active']


# Dashboard Overview for HRMS
class HRMSDashboardView(APIView):
    """
    Get HRMS dashboard overview
    GET /api/v1/hrms/dashboard/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        employees = Employee.objects.all()
        leaves = LeaveApplication.objects.filter(start_date__year=timezone.now().year)
        
        return Response({
            'employees': {
                'total': employees.count(),
                'active': employees.filter(employment_status='ACTIVE').count(),
                'on_leave': employees.filter(employment_status='ON_LEAVE').count(),
            },
            'leaves': {
                'pending': leaves.filter(status='PENDING').count(),
                'approved_this_month': leaves.filter(
                    status='APPROVED',
                    start_date__month=timezone.now().month
                ).count(),
            },
            'departments': Department.objects.count(),
            'recent_leaves': LeaveApplicationListSerializer(
                leaves.order_by('-created_at')[:5], many=True
            ).data,
        })

