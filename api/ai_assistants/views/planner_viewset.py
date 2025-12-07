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
from datetime import timedelta
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
from ai_assistants.services.planner_service import (
    handle_query_logic, 
    dataframe_cache, 
    load_all_datasets,
    ai_parse_tasks_from_text,
    ai_reprioritize_tasks,
    ai_suggest_schedule,
    calculate_ai_priority_score,
)

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
        AI creates tasks from free-form input using LLM.
        Parses natural language text into multiple structured tasks.
        """
        serializer = PlannerAICreateTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        input_text = serializer.validated_data['input_text']
        auto_prioritize = serializer.validated_data.get('auto_prioritize', True)
        auto_schedule = serializer.validated_data.get('auto_schedule', True)
        source_email_id = serializer.validated_data.get('source_email_id')
        
        user = request.user if request.user.is_authenticated else None
        
        # Build context for AI
        context = {}
        if source_email_id:
            context['source_email_id'] = str(source_email_id)
        if user:
            context['user_name'] = user.get_full_name() or user.username
        
        # Use AI to parse tasks from input text
        ai_result = ai_parse_tasks_from_text(input_text, context)
        
        created_tasks = []
        for task_data in ai_result.get('tasks', []):
            # Calculate suggested deadline
            deadline_days = task_data.get('suggested_deadline_days', 7)
            suggested_deadline = timezone.now().date() + timedelta(days=deadline_days)
            
            # Calculate AI priority score
            priority_score = calculate_ai_priority_score(task_data) if auto_prioritize else 50.0
            
            task = PlannerTask.objects.create(
                title=task_data.get('title', input_text[:100]),
                description=task_data.get('description', ''),
                priority=task_data.get('priority', 'MEDIUM'),
                due_date=suggested_deadline if auto_schedule else None,
                created_by=user,
                ai_generated=True,
                ai_priority_score=priority_score,
                ai_suggested_deadline=suggested_deadline,
                ai_reasoning=task_data.get('reasoning', 'AI-generated task from user input'),
                source_type='ai_create',
                source_id=str(source_email_id) if source_email_id else '',
                tags=task_data.get('tags', []),
            )
            created_tasks.append(task)
        
        # If no tasks were extracted, create a single task from input
        if not created_tasks:
            task = PlannerTask.objects.create(
                title=input_text[:100],
                description=input_text,
                created_by=user,
                ai_generated=True,
                ai_priority_score=50.0,
                ai_reasoning="Created from user input (no specific tasks identified)"
            )
            created_tasks.append(task)
        
        return Response({
            'tasks': PlannerTaskSerializer(created_tasks, many=True).data,
            'summary': ai_result.get('summary', f'Created {len(created_tasks)} task(s)'),
            'tasks_created': len(created_tasks),
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def ai_reprioritize(self, request):
        """
        AI reprioritizes all active tasks using LLM.
        Considers deadlines, dependencies, and workload balance.
        """
        serializer = PlannerAIReprioritizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        consider_deadlines = serializer.validated_data.get('consider_deadlines', True)
        consider_dependencies = serializer.validated_data.get('consider_dependencies', True)
        
        # Get active tasks
        tasks = self.get_queryset().filter(status__in=['TODO', 'IN_PROGRESS'])
        
        if not tasks.exists():
            return Response({
                'status': 'no_tasks',
                'message': 'No active tasks to reprioritize',
                'tasks_updated': 0,
            })
        
        # Convert tasks to list of dicts for AI processing
        task_list = []
        for task in tasks:
            task_list.append({
                'id': str(task.id),
                'title': task.title,
                'description': task.description,
                'priority': task.priority,
                'status': task.status,
                'due_date': task.due_date,
                'ai_priority_score': task.ai_priority_score,
                'tags': task.tags,
            })
        
        # Use AI to reprioritize
        ai_result = ai_reprioritize_tasks(
            task_list,
            options={
                'consider_deadlines': consider_deadlines,
                'consider_dependencies': consider_dependencies,
            }
        )
        
        # Apply new scores to tasks
        updated_count = 0
        score_map = {
            item['task_id']: item 
            for item in ai_result.get('reprioritized_tasks', [])
        }
        
        for task in tasks:
            task_id = str(task.id)
            if task_id in score_map:
                reprioritized = score_map[task_id]
                task.ai_priority_score = min(100, max(0, reprioritized.get('new_score', task.ai_priority_score)))
                task.ai_reasoning = reprioritized.get('reasoning', task.ai_reasoning)
                task.save()
                updated_count += 1
        
        return Response({
            'status': 'reprioritized',
            'message': ai_result.get('summary', f'Reprioritized {updated_count} tasks'),
            'tasks_updated': updated_count,
            'recommendations': ai_result.get('recommendations', []),
        })
    
    @action(detail=False, methods=['post'])
    def ai_schedule(self, request):
        """
        AI suggests an optimal schedule for tasks.
        """
        available_hours = request.data.get('available_hours_per_day', 8.0)
        
        # Get active tasks
        tasks = self.get_queryset().filter(status__in=['TODO', 'IN_PROGRESS'])
        
        if not tasks.exists():
            return Response({
                'schedule': [],
                'message': 'No active tasks to schedule',
            })
        
        # Convert tasks to list of dicts
        task_list = []
        for task in tasks:
            task_list.append({
                'id': str(task.id),
                'title': task.title,
                'priority': task.priority,
                'due_date': task.due_date,
                'ai_priority_score': task.ai_priority_score,
                'estimated_hours': 2.0,  # Default estimate
            })
        
        # Use AI to suggest schedule
        schedule_result = ai_suggest_schedule(task_list, available_hours)
        
        return Response(schedule_result)
    
    @action(detail=False, methods=['post'])
    def from_email(self, request):
        """
        Create tasks from an email.
        Uses AI to extract actionable items from email content.
        """
        from ai_assistants.models import Email
        
        email_id = request.data.get('email_id')
        if not email_id:
            return Response(
                {'error': 'email_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            email = Email.objects.get(id=email_id)
        except Email.DoesNotExist:
            return Response(
                {'error': 'Email not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user = request.user if request.user.is_authenticated else None
        
        # Prepare email content for AI
        email_content = f"""
From: {email.from_name} <{email.from_address}>
Subject: {email.subject}
Date: {email.received_at or email.created_at}

{email.body_text}
"""
        
        context = {
            'source_type': 'email',
            'source_email_id': str(email.id),
            'sender': email.from_address,
            'subject': email.subject,
        }
        
        # Use AI to parse tasks
        ai_result = ai_parse_tasks_from_text(email_content, context)
        
        created_tasks = []
        for task_data in ai_result.get('tasks', []):
            deadline_days = task_data.get('suggested_deadline_days', 7)
            suggested_deadline = timezone.now().date() + timedelta(days=deadline_days)
            priority_score = calculate_ai_priority_score(task_data)
            
            task = PlannerTask.objects.create(
                title=task_data.get('title', email.subject[:100]),
                description=task_data.get('description', ''),
                priority=task_data.get('priority', 'MEDIUM'),
                due_date=suggested_deadline,
                created_by=user,
                ai_generated=True,
                ai_priority_score=priority_score,
                ai_suggested_deadline=suggested_deadline,
                ai_reasoning=task_data.get('reasoning', f'Extracted from email: {email.subject}'),
                source_type='email',
                source_id=str(email.id),
                related_email=email,
                tags=task_data.get('tags', []),
            )
            created_tasks.append(task)
        
        return Response({
            'tasks': PlannerTaskSerializer(created_tasks, many=True).data,
            'summary': ai_result.get('summary', f'Created {len(created_tasks)} task(s) from email'),
            'tasks_created': len(created_tasks),
            'email_subject': email.subject,
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def from_event(self, request):
        """
        Create tasks from a calendar event.
        Uses AI to extract action items and follow-ups.
        """
        event_id = request.data.get('event_id')
        if not event_id:
            return Response(
                {'error': 'event_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            event = ScheduleEvent.objects.get(id=event_id)
        except ScheduleEvent.DoesNotExist:
            return Response(
                {'error': 'Event not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user = request.user if request.user.is_authenticated else None
        
        # Prepare event content for AI
        attendees = ', '.join(event.attendee_names or []) if hasattr(event, 'attendee_names') else ''
        event_content = f"""
Event: {event.title}
Date: {event.start_time.strftime('%Y-%m-%d %H:%M')} - {event.end_time.strftime('%H:%M')}
Location: {event.location or 'Not specified'}
Attendees: {attendees}

Description:
{event.description or 'No description provided'}

Please extract any action items, follow-ups, or tasks that should be created after this meeting.
"""
        
        context = {
            'source_type': 'event',
            'event_title': event.title,
            'event_date': str(event.start_time.date()),
        }
        
        # Use AI to parse tasks
        ai_result = ai_parse_tasks_from_text(event_content, context)
        
        created_tasks = []
        for task_data in ai_result.get('tasks', []):
            deadline_days = task_data.get('suggested_deadline_days', 7)
            suggested_deadline = timezone.now().date() + timedelta(days=deadline_days)
            priority_score = calculate_ai_priority_score(task_data)
            
            task = PlannerTask.objects.create(
                title=task_data.get('title', f'Follow-up: {event.title}'[:100]),
                description=task_data.get('description', ''),
                priority=task_data.get('priority', 'MEDIUM'),
                due_date=suggested_deadline,
                created_by=user,
                ai_generated=True,
                ai_priority_score=priority_score,
                ai_suggested_deadline=suggested_deadline,
                ai_reasoning=task_data.get('reasoning', f'Follow-up from event: {event.title}'),
                source_type='event',
                source_id=str(event.id),
                tags=task_data.get('tags', []) + ['meeting-followup'],
            )
            created_tasks.append(task)
        
        return Response({
            'tasks': PlannerTaskSerializer(created_tasks, many=True).data,
            'summary': ai_result.get('summary', f'Created {len(created_tasks)} task(s) from event'),
            'tasks_created': len(created_tasks),
            'event_title': event.title,
        }, status=status.HTTP_201_CREATED)
    
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

