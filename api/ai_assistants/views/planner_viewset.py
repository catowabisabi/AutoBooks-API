"""
Planner AI ViewSets
Task management with AI features
"""
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
import pandas as pd
import numpy as np
import logging

from ai_assistants.models import PlannerTask, ScheduleEvent
from ai_assistants.serializers.planner_serializer import (
    PlannerQuerySerializer,
    PlannerTaskSerializer, PlannerTaskListSerializer, PlannerTaskCreateSerializer,
    ScheduleEventSerializer, ScheduleEventCreateSerializer,
    PlannerAICreateTaskSerializer, PlannerAIReprioritizeSerializer
)
from ai_assistants.services.planner_service import handle_query_logic, dataframe_cache, load_all_datasets

logger = logging.getLogger(__name__)


def get_permission_classes():
    """Return permission classes based on DEBUG setting"""
    if settings.DEBUG:
        return [AllowAny()]
    return [IsAuthenticated()]


# Legacy views for backward compatibility
class StartDatasetLoadView(APIView):
    def get_permissions(self):
        return get_permission_classes()
    
    def get(self, request):
        try:
            result = load_all_datasets()
            return Response(result)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Allow POST for clients that default to POST for actions."""
        return self.get(request)


class PlannerDataView(APIView):
    def get_permissions(self):
        return get_permission_classes()
    
    def get(self, request):
        df = dataframe_cache.get("planner_data")
        if df is not None:
            df_copy = df.copy()
            df_copy = df_copy.replace([float('inf'), float('-inf')], None)
            df_copy = df_copy.replace({pd.NA: None, np.nan: None})
            return Response(df_copy.to_dict(orient="records"))
        return Response({"error": "No planner data found. Call /start first."}, status=status.HTTP_404_NOT_FOUND)


class PlannerQueryView(APIView):
    def get_permissions(self):
        return get_permission_classes()
    
    def post(self, request):
        serializer = PlannerQuerySerializer(data=request.data)
        if serializer.is_valid():
            query = serializer.validated_data["query"]
            result = handle_query_logic(query)
            return Response(result)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# New ViewSets
class PlannerTaskViewSet(viewsets.ModelViewSet):
    """
    Planner Task management with AI features
    """
    queryset = PlannerTask.objects.all()
    serializer_class = PlannerTaskSerializer
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        queryset = PlannerTask.objects.filter(is_active=True)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by priority
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by assigned user
        assigned_to = self.request.query_params.get('assigned_to')
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        
        # Filter by due date
        due_date = self.request.query_params.get('due_date')
        if due_date:
            queryset = queryset.filter(due_date=due_date)
        
        # Overdue tasks
        overdue = self.request.query_params.get('overdue')
        if overdue and overdue.lower() == 'true':
            queryset = queryset.filter(
                due_date__lt=timezone.now().date(),
                status__in=['TODO', 'IN_PROGRESS']
            )
        
        # AI generated only
        ai_generated = self.request.query_params.get('ai_generated')
        if ai_generated is not None:
            queryset = queryset.filter(ai_generated=ai_generated.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('-ai_priority_score', 'due_date', '-created_at')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PlannerTaskListSerializer
        if self.action == 'create':
            return PlannerTaskCreateSerializer
        return PlannerTaskSerializer
    
    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark task as completed"""
        task = self.get_object()
        task.status = 'DONE'
        task.completed_at = timezone.now()
        task.save()
        return Response({'status': 'completed'})
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start working on task"""
        task = self.get_object()
        task.status = 'IN_PROGRESS'
        task.save()
        return Response({'status': 'in_progress'})
    
    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        """Mark task as blocked"""
        task = self.get_object()
        task.status = 'BLOCKED'
        task.save()
        return Response({'status': 'blocked'})
    
    @action(detail=False, methods=['post'])
    def ai_create(self, request):
        """
        AI creates tasks from free-form input
        """
        serializer = PlannerAICreateTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        input_text = serializer.validated_data['input_text']
        
        # TODO: Integrate with AI service
        # For now, create a single task from input
        user = request.user if request.user.is_authenticated else None
        
        task = PlannerTask.objects.create(
            title=input_text[:100],
            description=input_text,
            created_by=user,
            ai_generated=True,
            ai_priority_score=50.0,
            ai_reasoning="Auto-created from user input"
        )
        
        return Response(
            PlannerTaskSerializer(task).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def ai_reprioritize(self, request):
        """
        AI reprioritizes all tasks
        """
        serializer = PlannerAIReprioritizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tasks = self.get_queryset().filter(status__in=['TODO', 'IN_PROGRESS'])
        
        # TODO: Integrate with AI service
        # For now, simple rule-based prioritization
        for task in tasks:
            score = 50.0
            
            # Boost overdue tasks
            if task.due_date and task.due_date < timezone.now().date():
                score += 30
            
            # Boost high priority
            if task.priority == 'CRITICAL':
                score += 25
            elif task.priority == 'HIGH':
                score += 15
            
            # Reduce low priority
            if task.priority == 'LOW':
                score -= 10
            
            task.ai_priority_score = min(100, max(0, score))
            task.ai_reasoning = "Reprioritized based on due date and priority level"
            task.save()
        
        return Response({
            'status': 'reprioritized',
            'tasks_updated': tasks.count()
        })
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get tasks due today"""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(due_date=today)
        serializer = PlannerTaskListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue tasks"""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(
            due_date__lt=today,
            status__in=['TODO', 'IN_PROGRESS']
        )
        serializer = PlannerTaskListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get task statistics"""
        queryset = self.get_queryset()
        today = timezone.now().date()
        return Response({
            'total': queryset.count(),
            'todo': queryset.filter(status='TODO').count(),
            'in_progress': queryset.filter(status='IN_PROGRESS').count(),
            'done': queryset.filter(status='DONE').count(),
            'overdue': queryset.filter(due_date__lt=today, status__in=['TODO', 'IN_PROGRESS']).count(),
            'due_today': queryset.filter(due_date=today).count(),
            'ai_generated': queryset.filter(ai_generated=True).count(),
        })


class ScheduleEventViewSet(viewsets.ModelViewSet):
    """
    Calendar event management
    """
    queryset = ScheduleEvent.objects.all()
    serializer_class = ScheduleEventSerializer
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        queryset = ScheduleEvent.objects.filter(is_active=True)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(start_time__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_time__date__lte=end_date)
        
        return queryset.order_by('start_time')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ScheduleEventCreateSerializer
        return ScheduleEventSerializer
    
    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(organizer=user)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's events"""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(start_time__date=today)
        serializer = ScheduleEventSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming events (next 7 days)"""
        from datetime import timedelta
        today = timezone.now().date()
        week_later = today + timedelta(days=7)
        queryset = self.get_queryset().filter(
            start_time__date__gte=today,
            start_time__date__lte=week_later
        )
        serializer = ScheduleEventSerializer(queryset, many=True)
        return Response(serializer.data)

